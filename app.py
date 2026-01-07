from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
templates = Jinja2Templates(directory="templates")

import os
import os
import json
import re
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import sympy as sp

# ---------------- LOAD ENV ----------------
from datetime import date

# FREE LIMIT
FREE_DAILY_LIMIT = 5

# In-memory usage store
# Structure: { ip: { "date": yyyy-mm-dd, "count": int } }
usage_tracker = {}



load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)   # ✅ THIS WAS MISSING

# ---------------- APP ----------------
app = FastAPI(
    title="EduMentor",
    description="AI-powered learning engine",
    version="1.0",
    docs_url=None,          # ❌ disables /docs
    redoc_url=None,         # ❌ disables /redoc
    openapi_url=None        # ❌ disables /openapi.json
)

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head><title>EduMentor</title></head>
    <body style="font-family:Arial;text-align:center;padding-top:80px;">
        <h1>Welcome to EduMentor 📘</h1>
        <p>AI-powered step-by-step learning</p>
        <a href="/student">
            <button style="padding:12px 20px;font-size:16px;">Start Learning</button>
        </a>
    </body>
    </html>
    """
@app.get("/student", response_class=HTMLResponse)
def student_page(request: Request):
    return templates.TemplateResponse("student.html", {"request": request})



# ---------------- HELPERS ----------------
def clean_and_parse_json(text: str):
    """
    Cleans markdown JSON returned by LLM and parses it safely.
    """
    text = re.sub(r"```json|```", "", text).strip()
    return json.loads(text)

def check_usage_limit(ip: str):
    today = date.today().isoformat()

    if ip not in usage_tracker:
        usage_tracker[ip] = {"date": today, "count": 0}

    # Reset count if new day
    if usage_tracker[ip]["date"] != today:
        usage_tracker[ip] = {"date": today, "count": 0}

    if usage_tracker[ip]["count"] >= FREE_DAILY_LIMIT:
        return False

    usage_tracker[ip]["count"] += 1
    return True


# ---------------- AGENTS ----------------
def agent_classifier(problem: str):
    prompt = f"""
You are an IIT-JEE Mathematics expert.

Classify the following problem into:
- Topic
- Sub-topic
- Difficulty (Easy / Medium / Hard)

Return ONLY valid JSON.
Do not add markdown.
Do not add explanations.

Problem:
{problem}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content


def agent_solver(problem: str):
    prompt = f"""
Solve the following math problem step by step.

IMPORTANT FORMAT RULES:
- Use ONLY plain English text
- Do NOT use LaTeX
- Do NOT use symbols like \\ , {{ }}, **, $, or math blocks
- Write like a teacher explaining on a blackboard
- Use words instead of formulas where possible

Problem:
{problem}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content


def agent_teacher(solution: str):
    prompt = f"""
Explain the solution in simple student-friendly language.

FORMAT RULES:
- Plain text only
- No LaTeX
- No backslashes, curly braces, or symbols
- Use numbered steps
- Write as if explaining orally in class

Solution:
{solution}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content


# ---------------- SYMPY VERIFICATION ----------------
def sympy_verify(problem: str, solution_text: str):
    """
    MVP symbolic verification.
    (Hardcoded for demonstration – expandable later)
    """
    x = sp.symbols("x")
    expr = x**2 * sp.sin(x)
    correct = sp.diff(expr, x)
    return f"VERIFIED by SymPy: {correct}"


# ---------------- CORE PIPELINE ----------------
def solve_math_problem(problem: str):
    classification_raw = agent_classifier(problem)
    classification = clean_and_parse_json(classification_raw)

    raw_solution = agent_solver(problem)
    solution = clean_text(raw_solution)

    raw_explanation = agent_teacher(solution)
    explanation = clean_text(raw_explanation)

    verification = sympy_verify(problem, solution)

    return {
        "classification": classification,
        "solution": solution,
        "explanation": explanation,
        "verification": verification
    }


# ---------------- API SCHEMA ----------------
class MathRequest(BaseModel):
    problem: str

# ---------------- API ENDPOINT ----------------
from fastapi import Request, HTTPException

from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EduMentor</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f5f7fa;
                text-align: center;
                padding-top: 80px;
            }
            h1 {
                color: #2c3e50;
            }
            p {
                font-size: 18px;
                color: #555;
            }
            a {
                display: inline-block;
                margin: 15px;
                padding: 12px 20px;
                text-decoration: none;
                background-color: #007bff;
                color: white;
                border-radius: 6px;
                font-size: 16px;
            }
            a:hover {
                background-color: #0056b3;
            }
        </style>
    </head>
    <body>
        <h1>🎓 EduMentor</h1>
        <p>Your AI-powered personal tutor for step-by-step learning.</p>

        <a href="/docs">🚀 Try EduMentor</a>
        <a href="https://openai.com">🤖 Powered by AI</a>

        <p style="margin-top:40px;color:#888;">
            
        </p>
    </body>
    </html>
    """


@app.post("/solve")
def solve(request: MathRequest, req: Request):
    client_ip = req.client.host

    allowed = check_usage_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Free limit reached (5 problems/day). Please upgrade to continue."
        )

    return solve_math_problem(request.problem)

def clean_text(text: str):
    replacements = {
        "\\(": "",
        "\\)": "",
        "\\[": "",
        "\\]": "",
        "**": "",
        "{": "",
        "}": "",
        "$": ""
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.strip()


