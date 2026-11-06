\# CV Analyzer API



A small REST API (FastAPI) that compares CV text with a job description using the Google Gemini API and returns a match score, matching and missing skills, strengths and suggestions as JSON.



\## Endpoints

\- GET /health returns {"status": "ok"}

\- POST /analyze takes {"cv\_text": "...", "job\_description": "..."} and returns the analysis



\## Run it

pip install -r requirements.txt

set the environment variable GEMINI\_API\_KEY to your own key

uvicorn main:app --reload

Then open http://127.0.0.1:8000/docs



\## Tests

pytest -v

The 8 tests replace the model with a fake one, so they need no API key and cost nothing. They check the response structure, input validation, unusable model answers, out-of-range scores, service failures and a missing key. I also checked the real call by hand.



\## Design notes

\- The model call is a separate function injected into the endpoint, so tests can replace it.

\- Retries with increasing waits, and a second model as a fallback, handle 503 errors.

\- Errors return clear status codes (422, 500, 502) and never show the key.

\- The API key is read from an environment variable and is never stored in the code.



\## Limitations

\- The score is an AI estimate, not an objective measure.

\- Only the first part of long inputs is sent to the model.

\- No authentication or rate limiting yet.

