"""
Integration tests for the Role-Based Skill Assessment story: connecting
Role-Based Question Generation to Interview Question Storage via

    POST /api/interview-questions/{interview_id}/generate

These tests exercise the real orchestration pipeline
(app.modules.interview_questions.pipeline) and the real storage layer
(InterviewQuestionService / InterviewQuestionRepository) against an
in-memory SQLite database containing just the two tables this feature
touches (``interviews`` and ``interview_questions``). The full model
metadata can't be created on SQLite -- other tables (e.g.
job_opportunities) use Postgres-only JSONB columns -- and the project has
no test-database fixture yet (see tests/test_screening_criteria_persistence.py),
so this fixture is scoped locally to this file.

The LLM/GPT layer itself is not re-tested here -- prompt building, raw
response parsing, and schema validation are already covered by
tests/test_question_generation.py. This file uses a fake
IQuestionGenerationService to control what the "existing generation
pipeline" returns, and asserts on what the "existing storage service"
persisted (and, for failure cases, what it did *not* persist).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models.interview import Interview
from app.database.models.interview_question import InterviewQuestion
from app.modules.interview_questions.router import (
    generate_and_store_interview_questions,
    get_interview_questions,
)
from app.schemas.interview_question import (
    InterviewQuestion as GeneratedInterviewQuestionItem,
    QuestionGenerationResponse,
)
from app.schemas.interview_question_storage import QuestionCategory
from app.schemas.question_generation import QuestionGenerationInput
from app.services.question_generation_service import (
    EmptyLLMResponseError,
    LLMProviderError,
    QuestionGenerationError,
)




# ---------------------------------------------------------------------------
# Fixtures / test doubles
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session():
    # Only the tables this feature touches -- see module docstring. FK
    # enforcement is intentionally left at SQLite's default (off): the
    # `applications` table Interview.application_id references isn't
    # created here, and this integration's own interview-existence check
    # (InterviewNotFoundError, exercised below) is what's under test --
    # not the database's FK enforcement, which Postgres already provides
    # in production.
    engine = create_engine("sqlite:///:memory:")

    Interview.__table__.create(engine)
    InterviewQuestion.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()


def _create_interview(db_session, interview_id: int) -> None:
    db_session.execute(
        Interview.__table__.insert().values(
            id=interview_id,
            application_id=1,
            scheduled_at=datetime.now(timezone.utc),
            status="scheduled",
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()


class FakeQuestionGenerationService:
    """Stands in for the existing generation pipeline's LLM-backed service.

    Implements the same IQuestionGenerationService contract
    (generate_questions(prompt, number_of_questions) -> QuestionGenerationResponse)
    without touching the real LLM client, prompt builder, or response
    parser -- those already have dedicated coverage in
    tests/test_question_generation.py.
    """

    def __init__(
        self,
        response: Optional[QuestionGenerationResponse] = None,
        error: Optional[Exception] = None,
    ):
        self.response = response
        self.error = error
        self.calls: list[tuple[str, int]] = []

    async def generate_questions(
        self,
        prompt: str,
        number_of_questions: int,
    ) -> QuestionGenerationResponse:
        self.calls.append((prompt, number_of_questions))

        if self.error:
            raise self.error

        assert self.response is not None
        return self.response


def make_generation_response(
    items: list[tuple[str, QuestionCategory, Optional[str]]],
) -> QuestionGenerationResponse:
    return QuestionGenerationResponse(
        questions=[
            GeneratedInterviewQuestionItem(
                question=question,
                category=category,
                skill=skill,
            )
            for question, category, skill in items
        ]
    )


def valid_input() -> dict:
    """Same shape as tests/test_question_generation.py::valid_input.

    Duplicated locally (rather than imported) so this file has no
    cross-test-module coupling.
    """
    return {
        "job_description": {
            "job_id": "job-123",
            "role": {
                "title": "Backend Engineer",
                "department": "Engineering",
                "employment_type": "Full-time",
                "location": "Remote",
            },
            "job_summary": "Build backend services.",
            "responsibilities": ["Develop APIs"],
            "requirements": {
                "skills": {
                    "required": ["Python"],
                    "preferred": [],
                },
                "experience": {
                    "minimum_years": 2,
                    "level": "Mid-level",
                },
                "education": [],
                "certifications": [],
                "languages": [],
            },
            "technical_stack": ["Python"],
            "soft_skills": [],
            "screening_settings": {
                "passing_score": 70,
            },
        },
        "screening_criteria": {
            "job_id": "job-123",
            "screening_criteria": {
                "skills": {
                    "weight": 50,
                    "required": [
                        {"name": "Python", "weight": 50},
                    ],
                    "preferred": [],
                },
                "experience": {
                    "weight": 25,
                    "minimum_years": 2,
                    "level": "Mid-level",
                },
                "education": {
                    "weight": 10,
                    "preferred_fields": [],
                },
                "projects": {
                    "weight": 5,
                    "required": False,
                    "relevant_domains": [],
                },
                "certifications": {
                    "weight": 3,
                    "criteria": [],
                },
                "languages": {
                    "weight": 2,
                    "criteria": [],
                },
                "soft_skills": {
                    "weight": 5,
                    "criteria": [],
                },
            },
            "passing_score": 70,
        },
    }


def make_structured_request() -> QuestionGenerationInput:
    return QuestionGenerationInput.model_validate(valid_input())


# ---------------------------------------------------------------------------
# 1 & 7. Valid interview: questions generated, stored, and fields preserved
# ---------------------------------------------------------------------------


class TestGenerateAndStoreSuccess:

    @pytest.mark.asyncio
    async def test_valid_existing_interview_generates_and_stores_questions(
        self, db_session
    ):
        _create_interview(db_session, interview_id=1)

        generation = FakeQuestionGenerationService(
            response=make_generation_response(
                [
                    (
                        "Explain dependency injection in FastAPI.",
                        QuestionCategory.SKILLS,
                        "FastAPI",
                    ),
                    (
                        "Tell me about a challenging backend project.",
                        QuestionCategory.PROJECTS,
                        None,
                    ),
                ]
            )
        )

        result = await generate_and_store_interview_questions(
            interview_id=1,
            request=make_structured_request(),
            generation_service=generation,
            db=db_session,
        )

        assert len(result.questions) == 2
        assert generation.calls, "generation pipeline was never invoked"


    @pytest.mark.asyncio
    async def test_stored_questions_preserve_all_required_fields(
        self, db_session
    ):
        _create_interview(db_session, interview_id=1)

        generation = FakeQuestionGenerationService(
            response=make_generation_response(
                [
                    (
                        "What's your experience with PostgreSQL?",
                        QuestionCategory.SKILLS,
                        "PostgreSQL",
                    ),
                ]
            )
        )

        result = await generate_and_store_interview_questions(
            interview_id=1,
            request=make_structured_request(),
            generation_service=generation,
            db=db_session,
        )

        question = result.questions[0]

        assert question.question_text == "What's your experience with PostgreSQL?"
        assert question.question_type == "skills"
        assert question.skill == "PostgreSQL"
        assert question.sequence_number == 1
        assert question.is_follow_up is False
        assert question.parent_question_id is None


# ---------------------------------------------------------------------------
# 2. GET after generate returns the stored questions, correctly ordered
# ---------------------------------------------------------------------------


class TestGetAfterGenerate:
    @pytest.mark.asyncio
    async def test_get_returns_stored_questions_in_sequence_order(
        self, db_session
    ):
        _create_interview(db_session, interview_id=1)

        generation = FakeQuestionGenerationService(
            response=make_generation_response(
                [
                    ("Question A?", QuestionCategory.SKILLS, "Python"),
                    ("Question B?", QuestionCategory.EXPERIENCE, None),
                    ("Question C?", QuestionCategory.SOFT_SKILLS, None),
                ]
            )
        )

        await generate_and_store_interview_questions(
            interview_id=1,
            request=make_structured_request(),
            generation_service=generation,
            db=db_session,
        )

        fetched = get_interview_questions(interview_id=1, db=db_session)

        assert [q.sequence_number for q in fetched.questions] == [1, 2, 3]
        assert [q.question_text for q in fetched.questions] == [
            "Question A?",
            "Question B?",
            "Question C?",
        ]


# ---------------------------------------------------------------------------
# 3. Invalid interview_id -> 404, nothing stored
# ---------------------------------------------------------------------------


class TestInvalidInterviewId:
    @pytest.mark.asyncio
    async def test_missing_interview_returns_404(self, db_session):
        generation = FakeQuestionGenerationService(
            response=make_generation_response(
                [("Question?", QuestionCategory.SKILLS, None)]
            )
        )

        with pytest.raises(HTTPException) as exc_info:
            await generate_and_store_interview_questions(
                interview_id=999,
                request=make_structured_request(),
                generation_service=generation,
                db=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_missing_interview_stores_nothing(self, db_session):
        generation = FakeQuestionGenerationService(
            response=make_generation_response(
                [("Question?", QuestionCategory.SKILLS, None)]
            )
        )

        with pytest.raises(HTTPException):
            await generate_and_store_interview_questions(
                interview_id=999,
                request=make_structured_request(),
                generation_service=generation,
                db=db_session,
            )

        fetched = get_interview_questions(interview_id=999, db=db_session)
        assert fetched.questions == []

    @pytest.mark.asyncio
    async def test_missing_interview_does_not_create_one(self, db_session):
        generation = FakeQuestionGenerationService(
            response=make_generation_response(
                [("Question?", QuestionCategory.SKILLS, None)]
            )
        )

        with pytest.raises(HTTPException):
            await generate_and_store_interview_questions(
                interview_id=999,
                request=make_structured_request(),
                generation_service=generation,
                db=db_session,
            )

        assert db_session.get(Interview, 999) is None


# ---------------------------------------------------------------------------
# 4. Mismatched job description / screening criteria job ids
# ---------------------------------------------------------------------------


class TestMismatchedJobIds:
    """
    QuestionGenerationInput is a FastAPI request-body parameter on this
    endpoint, so FastAPI/Pydantic validates it -- including the existing
    "must belong to the same job" rule -- before the endpoint body (and
    therefore the generation pipeline) ever runs. The validator itself is
    already covered by
    TestQuestionGenerationInput.test_rejects_different_job_ids in
    tests/test_question_generation.py; these tests confirm the same
    guarantee holds for this integration and that generation is never
    reached when it fails.
    """

    @pytest.mark.asyncio
    async def test_mismatched_job_ids_are_rejected_by_the_existing_validator(self):
        data = valid_input()
        data["screening_criteria"]["job_id"] = "a-different-job"

        with pytest.raises(ValidationError, match="must belong to the same job"):
            QuestionGenerationInput.model_validate(data)

    @pytest.mark.asyncio
    async def test_generation_service_is_never_reached_for_mismatched_ids(self):
        generation = FakeQuestionGenerationService(
            response=make_generation_response(
                [("Question?", QuestionCategory.SKILLS, None)]
            )
        )

        data = valid_input()
        data["screening_criteria"]["job_id"] = "a-different-job"

        with pytest.raises(ValidationError):
            QuestionGenerationInput.model_validate(data)

        # No valid QuestionGenerationInput could be built, so there is no
        # way to reach generate_and_store_interview_questions with it --
        # the fake was never called.
        assert generation.calls == []


# ---------------------------------------------------------------------------
# 5. GPT / provider failure -> existing API error, nothing stored
# ---------------------------------------------------------------------------


class TestGenerationProviderFailure:
    @pytest.mark.asyncio
    async def test_llm_provider_failure_maps_to_503(self, db_session):
        _create_interview(db_session, interview_id=1)

        generation = FakeQuestionGenerationService(
            error=LLMProviderError("LLM provider call failed: boom")
        )

        with pytest.raises(HTTPException) as exc_info:
            await generate_and_store_interview_questions(
                interview_id=1,
                request=make_structured_request(),
                generation_service=generation,
                db=db_session,
            )

        assert (
            exc_info.value.status_code
            == status.HTTP_503_SERVICE_UNAVAILABLE
        )

    @pytest.mark.asyncio
    async def test_invalid_llm_response_maps_to_502(self, db_session):
        _create_interview(db_session, interview_id=1)

        generation = FakeQuestionGenerationService(
            error=EmptyLLMResponseError("LLM returned an empty response.")
        )

        with pytest.raises(HTTPException) as exc_info:
            await generate_and_store_interview_questions(
                interview_id=1,
                request=make_structured_request(),
                generation_service=generation,
                db=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_502_BAD_GATEWAY

    @pytest.mark.asyncio
    async def test_provider_failure_stores_nothing(self, db_session):
        _create_interview(db_session, interview_id=1)

        generation = FakeQuestionGenerationService(
            error=LLMProviderError("boom")
        )

        with pytest.raises(HTTPException):
            await generate_and_store_interview_questions(
                interview_id=1,
                request=make_structured_request(),
                generation_service=generation,
                db=db_session,
            )

        fetched = get_interview_questions(interview_id=1, db=db_session)
        assert fetched.questions == []


# ---------------------------------------------------------------------------
# 6. Second initial generation for the same interview -> no duplicates
# ---------------------------------------------------------------------------


class TestDuplicateInitialGeneration:
    @pytest.mark.asyncio
    async def test_second_initial_generation_returns_409(self, db_session):
        _create_interview(db_session, interview_id=1)
        request = make_structured_request()

        first_response = make_generation_response(
            [("Question 1?", QuestionCategory.SKILLS, None)]
        )
        await generate_and_store_interview_questions(
            interview_id=1,
            request=request,
            generation_service=FakeQuestionGenerationService(
                response=first_response
            ),
            db=db_session,
        )

        second_response = make_generation_response(
            [("Question 2?", QuestionCategory.SKILLS, None)]
        )

        with pytest.raises(HTTPException) as exc_info:
            await generate_and_store_interview_questions(
                interview_id=1,
                request=request,
                generation_service=FakeQuestionGenerationService(
                    response=second_response
                ),
                db=db_session,
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_retry_does_not_create_a_duplicate_question_set(
        self, db_session
    ):
        _create_interview(db_session, interview_id=1)
        request = make_structured_request()

        response = make_generation_response(
            [("Question 1?", QuestionCategory.SKILLS, None)]
        )

        await generate_and_store_interview_questions(
            interview_id=1,
            request=request,
            generation_service=FakeQuestionGenerationService(
                response=response
            ),
            db=db_session,
        )

        with pytest.raises(HTTPException):
            await generate_and_store_interview_questions(
                interview_id=1,
                request=request,
                generation_service=FakeQuestionGenerationService(
                    response=response
                ),
                db=db_session,
            )

        fetched = get_interview_questions(interview_id=1, db=db_session)
        assert len(fetched.questions) == 1
