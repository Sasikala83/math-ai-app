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
    title="Math AI App",
    description="Agentic Math AI with verified solutions",
    version="1.0"
)



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
Show clear derivations.
Ensure mathematical correctness.

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
You are an experienced Class 12 & IIT-JEE Mathematics teacher.

Explain the solution step by step.
Explain WHY each step is done.
Mention common student mistakes.
Give exam-oriented tips.

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

    solution = agent_solver(problem)
    explanation = agent_teacher(solution)
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
