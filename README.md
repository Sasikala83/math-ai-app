# EduMentor 🚀

EduMentor is an AI-powered educational platform designed to help students
learn and master subjects like **Mathematics**, with plans to expand into
**Physics, Chemistry, and Computer Science**.

## 🔹 Current Features
- Step-by-step mathematical problem solving
- IIT-JEE / Class 11–12 focused explanations
- Topic classification & difficulty analysis
- Symbolic verification using SymPy

## 🔹 Technology Stack
- FastAPI
- OpenAI API
- SymPy
- Render (Deployment)

## 🔹 API Endpoint
POST `/solve`

Example request:
```json
{
  "problem": "Find the derivative of x^2 sin x"
}
