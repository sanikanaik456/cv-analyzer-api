import json

from fastapi.testclient import TestClient

from main import app, get_model_caller

client = TestClient(app)

CV = "Python developer with a Master's degree in data science and two projects using PyTorch."
JD = "We need a data scientist who knows Python, SQL and machine learning."

GOOD_ANSWER = json.dumps({
    "match_score": 78,
    "matching_skills": ["Python", "Machine learning"],
    "missing_skills": ["SQL"],
    "strengths": ["PyTorch projects"],
    "improvements": ["Add SQL experience"],
    "summary": "Good match with one gap.",
})


def use_fake_model(answer=None, error=None, seen=None):
    def fake(prompt):
        if seen is not None:
            seen.append(prompt)
        if error:
            raise error
        return answer
    app.dependency_overrides[get_model_caller] = lambda: fake


def teardown_function():
    app.dependency_overrides.clear()


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_returns_structured_result():
    use_fake_model(answer=GOOD_ANSWER)
    response = client.post("/analyze", json={"cv_text": CV, "job_description": JD})
    assert response.status_code == 200
    body = response.json()
    assert body["match_score"] == 78
    assert body["missing_skills"] == ["SQL"]


def test_prompt_contains_cv_and_job_description():
    seen = []
    use_fake_model(answer=GOOD_ANSWER, seen=seen)
    client.post("/analyze", json={"cv_text": CV, "job_description": JD})
    assert CV in seen[0]
    assert JD in seen[0]


def test_rejects_input_that_is_too_short():
    use_fake_model(answer=GOOD_ANSWER)
    response = client.post("/analyze", json={"cv_text": "hi", "job_description": JD})
    assert response.status_code == 422


def test_model_returns_text_that_is_not_json():
    use_fake_model(answer="Sorry, I cannot help with that.")
    response = client.post("/analyze", json={"cv_text": CV, "job_description": JD})
    assert response.status_code == 502


def test_score_out_of_range_is_rejected():
    bad = json.loads(GOOD_ANSWER)
    bad["match_score"] = 150
    use_fake_model(answer=json.dumps(bad))
    response = client.post("/analyze", json={"cv_text": CV, "job_description": JD})
    assert response.status_code == 502


def test_model_service_failure():
    use_fake_model(error=Exception("503 UNAVAILABLE"))
    response = client.post("/analyze", json={"cv_text": CV, "job_description": JD})
    assert response.status_code == 502


def test_missing_api_key():
    use_fake_model(error=RuntimeError("GEMINI_API_KEY is not set"))
    response = client.post("/analyze", json={"cv_text": CV, "job_description": JD})
    assert response.status_code == 500