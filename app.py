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

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)   # ✅ THIS WAS MISSING

# ---------------- APP ----------------
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("student.html", {"request": request})

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

# ---------------- AGENTS ----------------
def agent_classifier(problem: str):
    prompt = f"""
You are an expert Mathematics teacher for Classes 9 to 12 and IIT-JEE.

Classify the following problem into:
- Class (9 / 10 / 11 / 12 / JEE)
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



def agent_solver(problem: str, class_level: str, chapter: str):
    exam_style = get_exam_style(class_level)

    prompt = f"""
You are an experienced Mathematics teacher.

Exam Type: {class_level}
Chapter: {chapter}
Teaching Style: {exam_style}

Solve the following problem.

FORMAT:
given:
to find:
formula used:
solution:
step 1:
step 2:
...
therefore,
final answer:

Rules:
- Step-by-step
- Suitable for {class_level} level
- Follow the teaching style strictly

Problem:
{problem}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content


def agent_teacher(solution: str, class_level: str, chapter: str):
    exam_style = get_exam_style(class_level)

    prompt = f"""
You are teaching in a classroom.

Exam Type: {class_level}
Chapter: {chapter}
Teaching Style: {exam_style}

Explain the solution orally.

Rules:
- Very clear
- Stepwise
- According to {class_level} exam pattern
- Focus on understanding

Solution:
{solution}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content


def agent_logical_verifier(problem: str, solution: str, class_level: str, chapter: str):
    prompt = f"""
You are an examiner checking a student's answer.

Class: {class_level}
Chapter: {chapter}

Problem:
{problem}

Student Solution:
{solution}

Task:
1. Re-solve the problem independently.
2. Compare your final answer with the student's final answer.
3. State clearly whether the answer is correct.
4. Give a short verification statement.

Format:

verification:
status: correct / incorrect
reason:
(short logical justification)
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content



# ---------------- SYMPY VERIFICATION ----------------
def sympy_verify(problem: str, solution_text: str):
    x = sp.symbols("x")

    expr = sp.sympify(
        problem.replace("⁴","**4")
               .replace("³","**3")
               .replace("²","**2")
    )

    result = sp.diff(expr, x)

    pretty = str(result)
    pretty = pretty.replace("**4","⁴").replace("**3","³").replace("**2","²")

    return f"""verified:

f′(x) = {pretty}
"""



# ---------------- CORE PIPELINE ----------------
def solve_math_problem(problem: str, class_level: str = None, chapter: str = None):
    classification_raw = agent_classifier(problem)
    classification = clean_and_parse_json(classification_raw)

    raw_solution = agent_solver(problem, class_level, chapter)
    solution = clean_text(raw_solution)

    raw_explanation = agent_teacher(solution, class_level, chapter)
    explanation = clean_text(raw_explanation)

    try:
        if any(word in problem.lower() for word in ["differentiate", "derivative", "integrate", "integration"]):
            verification = sympy_verify(problem, solution)
        else:
            verification = agent_logical_verifier(problem, solution, class_level, chapter)
    except:
        verification = "verification could not be completed"

    return {
        "classification": classification,
        "class": class_level,
        "chapter": chapter,
        "solution": solution,
        "explanation": explanation,
        "verification": verification
    }


# ---------------- API SCHEMA ----------------
class MathRequest(BaseModel):
    problem: str
    class_level: str | None = None
    chapter: str | None = None

from fastapi.responses import RedirectResponse

@app.get("/")
def home():
    return RedirectResponse(url="/student")


@app.get("/student", response_class=HTMLResponse)
def student_page(request: Request):
    return templates.TemplateResponse("student.html", {"request": request})


@app.post("/solve")
def solve(request: MathRequest):
    return solve_math_problem(request.problem, request.class_level, request.chapter)


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

def get_exam_style(class_level: str):
    if class_level == "GATE":
        return "Use university level theory, rigorous derivations, and competitive exam depth."
    elif class_level == "CAT":
        return "Use fast methods, mental math shortcuts, and time-saving tricks."
    elif class_level == "UPSC CSAT":
        return "Use conceptual explanation, logical reasoning, and real-life interpretation."
    elif class_level == "JEE":
        return "Use high-level problem solving with concept linking and formula derivations."
    elif class_level == "Engineering":
        return "Use professor-style explanation with proofs and applications."
    else:
        return "Use simple school-level board exam explanation."

