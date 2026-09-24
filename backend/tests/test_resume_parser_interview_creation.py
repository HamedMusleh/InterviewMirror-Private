import asyncio
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import UploadFile
from starlette.datastructures import Headers

from app.modules.resume_parser.pipeline import ParsedCandidateResult
from app.modules.resume_parser import router as resume_parser_router
from app.modules.resume_parser.router import parse_candidate_cv
from app.schemas.resume import ResumeSchema
from app.schemas.screening_score import ScreeningScoreResponse
from app.services.interview_creation_service import InterviewCreationResult


CATEGORY_NAMES = (
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "languages",
    "soft_skills",
)


class FakeSession:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.saved = []

    def add(self, model):
        self.saved.append(model)

    def commit(self):
        self.commits += 1

    def flush(self):
        pass

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, model):
        model.id = 18


def _upload():
    return UploadFile(
        file=BytesIO(b"fake PDF"),
        filename="candidate.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )


def _parsed_candidate():
    return ParsedCandidateResult(
        resume_data=ResumeSchema(candidate_id="42"),
        semantic_sections={"skills": "Python"},
        embedding_vectors={"skills": [0.1, 0.2]},
        hard_requirements={"experience": []},
    )


def _matching_result():
    matching_results = MagicMock()
    matching_results.model_dump.return_value = {"skills": {"score": 90}}

    return SimpleNamespace(
        candidate_id="42",
        job_id="JOB-1",
        application_id=7,
        criteria_id=5,
        category_scores={
            name: {"score": 90, "status": "evaluated"}
            for name in CATEGORY_NAMES
        },
        category_weights={
            "skills": 40,
            "experience": 20,
            "education": 10,
            "projects": 10,
            "certifications": 5,
            "languages": 5,
            "soft_skills": 10,
        },
        matching_results=matching_results,
        passing_score=70,
    )


def _screening_result(final_status):
    return ScreeningScoreResponse(
        candidate_id="42",
        job_id="JOB-1",
        application_id=7,
        criteria_id=5,
        category_breakdown={
            name: {
                "score": 90,
                "weight": 10,
                "weighted_score": 9,
                "status": "evaluated",
            }
            for name in CATEGORY_NAMES
        },
        matched_criteria=list(CATEGORY_NAMES),
        missing_criteria=[],
        matching_details={},
        overall_score=90,
        passing_score=70,
        final_status=final_status,
    )


def _interview():
    now = datetime(2026, 9, 2, 8, 0, tzinfo=timezone.utc)

    return SimpleNamespace(
        id=31,
        application_id=7,
        scheduled_at=now,
        started_at=None,
        ended_at=None,
        status="scheduled",
        created_at=now,
    )


def _run_parse(final_status):
    parser = MagicMock()
    parser.parse.return_value = _parsed_candidate()

    matching_pipeline = MagicMock()
    matching_pipeline.match_application = AsyncMock()
    matching_pipeline.match_application.return_value = _matching_result()

    screening_pipeline = MagicMock()
    screening_pipeline.score_candidate.return_value = _screening_result(
        final_status
    )

    interview_service = MagicMock()
    interview_service.create_for_application.return_value = (
        InterviewCreationResult(
            interview=_interview(),
            created=True,
        )
    )

    db = FakeSession()

    # Generation is an LLM call with its own tests; stubbing it keeps this
    # test about whether an accepted candidate gets an interview at all.
    generate = AsyncMock(return_value=5)

    with patch.object(
        resume_parser_router, "ensure_interview_questions", generate
    ):
        result = asyncio.run(
            parse_candidate_cv(
                application_id=7,
                file=_upload(),
                pipeline=parser,
                matching_pipeline=matching_pipeline,
                screening_pipeline=screening_pipeline,
                interview_creation_service=interview_service,
                question_generation_service=MagicMock(),
                db=db,
            )
        )

    return result, interview_service, db, generate


def test_recommended_cv_creates_and_returns_the_interview():
    response, interview_service, db, generate = _run_parse("recommended")

    interview_service.create_for_application.assert_called_once_with(
        application_id=7
    )
    generate.assert_awaited_once()

    assert response["screening_result"].final_status == "recommended"
    assert response["interview"].created is True
    assert response["interview"].interview.id == 31
    assert db.commits == 1
    assert db.rollbacks == 0


def test_not_recommended_cv_does_not_create_an_interview():
    response, interview_service, db, generate = _run_parse("not_recommended")

    interview_service.create_for_application.assert_not_called()
    generate.assert_not_awaited()

    assert response["screening_result"].final_status == "not_recommended"
    assert response["interview"] is None
    assert db.commits == 1
    assert db.rollbacks == 0
