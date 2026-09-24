import json
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.modules.resume_matching.router import router


load_dotenv()


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _configured(*names: str) -> bool:
    return any(os.getenv(name) for name in names)


LIVE_TEST_ENABLED = os.getenv("RUN_LIVE_AI_TESTS") == "1" and all(
    (
        _configured("AZURE_OPENAI_ENDPOINT"),
        _configured("AZURE_OPENAI_KEY", "AZURE_OPENAI_API_KEY"),
        _configured("AZURE_OPENAI_API_VERSION"),
        _configured(
            "AZURE_OPENAI_DEPLOYMENT_NAME",
            "AZURE_OPENAI_DEPLOYMENT",
        ),
    )
)


def load_fixture(name: str) -> dict:
    with (FIXTURE_DIR / name).open(encoding="utf-8") as fixture:
        return json.load(fixture)


@pytest.mark.skipif(
    not LIVE_TEST_ENABLED,
    reason=(
        "Set RUN_LIVE_AI_TESTS=1 and the existing AZURE_OPENAI_* variables "
        "to run this test"
    ),
)
@pytest.mark.parametrize(
    "fixture_name",
    ["strong_match_request.json", "partial_match_request.json"],
)
def test_mock_fixture_against_live_azure_openai(fixture_name: str):
    test_app = FastAPI()
    test_app.include_router(router)

    response = TestClient(test_app).post(
        "/api/resume-matching",
        json=load_fixture(fixture_name),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    request = load_fixture(fixture_name)
    assert body["candidate_id"] == request["resume"]["candidate_id"]
    assert body["job_id"] == request["screening_criteria"]["job_id"]

    results = body["matching_results"]
    expected_categories = {
        "skills",
        "experience",
        "projects",
        "education",
        "certifications",
        "languages",
        "soft_skills",
    }
    assert set(results) == expected_categories

    for category in results.values():
        if category["status"] == "not_applicable":
            assert category["score"] is None
        else:
            assert 0 <= category["score"] <= 100

    required_skills = results["skills"]["required"]
    assert required_skills
    assert all(
        0 <= item["similarity_score"] <= 100 for item in required_skills
    )
    assert all("evidence" in item for item in required_skills)

    if fixture_name.startswith("partial"):
        assert results["experience"]["candidate_years"] < results["experience"]["required_years"]
        assert results["certifications"]["missing"]
        assert results["languages"]["missing"]
