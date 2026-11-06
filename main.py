import json
import os
import time

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

MODELS = ["gemini-3.5-flash", "gemini-3.7-flash"]
MAX_TRIES = 3

app = FastAPI(title="CV Analyzer API")


class AnalyzeRequest(BaseModel):
    cv_text: str = Field(min_length=20)
    job_description: str = Field(min_length=20)


class AnalyzeResponse(BaseModel):
    match_score: int = Field(ge=0, le=100)
    matching_skills: list[str]
    missing_skills: list[str]
    strengths: list[str]
    improvements: list[str]
    summary: str


def build_prompt(cv_text, job_description):
    return f"""You are an expert CV reviewer.
Compare the CV with the job description. Only use facts that appear in the CV.
Reply with valid JSON only, in exactly this shape:
{{
  "match_score": 0-100,
  "matching_skills": ["..."],
  "missing_skills": ["..."],
  "strengths": ["..."],
  "improvements": ["..."],
  "summary": "2-3 sentences"
}}

CV:
{cv_text[:4000]}

JOB DESCRIPTION:
{job_description[:3000]}"""


def parse_json(text):
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON.")
    return json.loads(text[start:end + 1])


def call_gemini(prompt):
    """The real model call, with retries. The tests replace this."""
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    client = genai.Client(api_key=api_key)
    last_error = None
    for model in MODELS:
        for attempt in range(MAX_TRIES):
            try:
                return client.models.generate_content(model=model, contents=prompt).text
            except Exception as e:
                last_error = e
                msg = str(e)
                if "503" in msg or "UNAVAILABLE" in msg or "429" in msg:
                    time.sleep(2 * (attempt + 1))
                else:
                    raise
    raise last_error


def get_model_caller():
    return call_gemini


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest, caller=Depends(get_model_caller)):
    prompt = build_prompt(request.cv_text, request.job_description)
    try:
        raw = caller(prompt)
        return AnalyzeResponse(**parse_json(raw))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Server is missing its API key.")
    except ValueError:
        raise HTTPException(status_code=502, detail="The model returned an unusable answer.")
    except Exception:
        raise HTTPException(status_code=502, detail="The model service is unavailable.")