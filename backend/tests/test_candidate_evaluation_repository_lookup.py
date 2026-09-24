"""
Unit tests for the two read methods added to CandidateEvaluationRepository
(app/repositories/candidate_evaluation_repository.py) so
CandidateReportHandler can validate and link against candidate_evaluations:

- get_by_id(candidate_evaluation_id)
- get_by_interview_id(interview_id)

These are additive - they don't touch or exercise
create_answer_evaluation / get_interview_evaluations /
get_candidate_interview_evaluations / create_candidate_evaluation /
get_by_candidate_id, which already have their own coverage elsewhere.
"""

from unittest.mock import MagicMock

from app.repositories.candidate_evaluation_repository import (
    CandidateEvaluationRepository,
)


def test_get_by_id_found():
    db = MagicMock()
    expected = object()
    db.scalar.return_value = expected

    repository = CandidateEvaluationRepository(db)

    assert repository.get_by_id(1) is expected
    db.scalar.assert_called_once()


def test_get_by_id_not_found():
    db = MagicMock()
    db.scalar.return_value = None

    repository = CandidateEvaluationRepository(db)

    assert repository.get_by_id(999) is None


def test_get_by_interview_id_found():
    db = MagicMock()
    expected = object()
    db.scalar.return_value = expected

    repository = CandidateEvaluationRepository(db)

    assert repository.get_by_interview_id(4) is expected
    db.scalar.assert_called_once()


def test_get_by_interview_id_not_found():
    db = MagicMock()
    db.scalar.return_value = None

    repository = CandidateEvaluationRepository(db)

    assert repository.get_by_interview_id(999) is None
