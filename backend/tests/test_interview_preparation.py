"""
Tests for filling a new interview with its questions.

The behaviour worth pinning down is what happens when generation goes wrong.
An accepted candidate's interview is committed before this runs, so a failed
LLM call must cost them their questions and nothing else — never the
interview, and never an exception that turns a successful acceptance into a
500.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.interviews import preparation
from app.modules.interviews.preparation import ensure_interview_questions


def run(db, generation_service=None):
    return asyncio.run(
        ensure_interview_questions(
            interview_id=31,
            db=db,
            generation_service=generation_service or MagicMock(),
        )
    )


def test_questions_are_generated_and_committed():
    db = MagicMock()

    with patch.object(
        preparation, "InterviewQuestionRepository"
    ) as repository, patch.object(
        preparation,
        "run_interview_question_generation_pipeline",
        AsyncMock(return_value=[object(), object(), object()]),
    ):
        repository.return_value.has_initial_questions.return_value = False

        assert run(db) == 3

    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_an_interview_that_already_has_questions_is_left_alone():
    """Re-running must not raise on the duplicate-question-set guard."""

    db = MagicMock()
    pipeline = AsyncMock()

    with patch.object(
        preparation, "InterviewQuestionRepository"
    ) as repository, patch.object(
        preparation,
        "run_interview_question_generation_pipeline",
        pipeline,
    ):
        repository.return_value.has_initial_questions.return_value = True
        repository.return_value.get_by_interview_id.return_value = [
            object(),
            object(),
        ]

        assert run(db) == 2

    pipeline.assert_not_awaited()
    db.commit.assert_not_called()


def test_a_generation_failure_does_not_lose_the_interview():
    """
    The interview is committed before this runs. A failure here must roll
    back only the generation attempt and report zero, so the caller can tell
    the candidate has an interview but no questions yet.
    """

    db = MagicMock()

    with patch.object(
        preparation, "InterviewQuestionRepository"
    ) as repository, patch.object(
        preparation,
        "run_interview_question_generation_pipeline",
        AsyncMock(side_effect=RuntimeError("the LLM was unreachable")),
    ):
        repository.return_value.has_initial_questions.return_value = False

        assert run(db) == 0

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_a_missing_interview_is_reported_rather_than_raised():
    db = MagicMock()

    with patch.object(
        preparation, "InterviewQuestionRepository"
    ) as repository, patch.object(
        preparation,
        "run_interview_question_generation_pipeline",
        AsyncMock(side_effect=LookupError("interview 31 does not exist")),
    ):
        repository.return_value.has_initial_questions.return_value = False

        assert run(db) == 0

    db.rollback.assert_called_once()


def test_the_pipeline_receives_the_interview_it_was_asked_about():
    db = MagicMock()
    pipeline = AsyncMock(return_value=[])
    generation_service = MagicMock()

    with patch.object(
        preparation, "InterviewQuestionRepository"
    ) as repository, patch.object(
        preparation,
        "run_interview_question_generation_pipeline",
        pipeline,
    ):
        repository.return_value.has_initial_questions.return_value = False

        run(db, generation_service)

    kwargs = pipeline.await_args.kwargs

    assert kwargs["interview_id"] == 31
    assert kwargs["db"] is db
    assert kwargs["generation_service"] is generation_service
