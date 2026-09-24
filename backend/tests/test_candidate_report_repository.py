"""
Unit tests for the storage layer added for the Candidate Report feature:

- CandidateReportRepository.save persists exactly the fields the
  candidate_reports table owns (candidate_evaluation_id, summary,
  strengths, areas_for_improvement, recommendation) and follows the
  project's commit / refresh / rollback-on-failure transaction pattern.
- CandidateReportRepository.get_by_candidate_evaluation_id looks up a
  report by candidate_evaluation_id.
- CandidateRepository.get_by_id / UserRepository.get_by_id follow the
  existing minimal get_by_id pattern (see InterviewRepository,
  ApplicationRepository).

These are unit tests against mocked SQLAlchemy Sessions, mirroring the
Mock-based style already used in tests/test_screening_criteria_persistence.py
and tests/test_resume_parser.py, since the project has no test-database
fixture.
"""

from unittest.mock import MagicMock

from app.database.models.candidate import Candidate
from app.database.models.user import User
from app.repositories.candidate_report_repository import (
    CandidateReportRepository,
)
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.user_repository import UserRepository
from app.schemas.candidate_report import CandidateReport


def _report() -> CandidateReport:
    return CandidateReport(
        candidate_evaluation_id=1,
        interview_id=4,
        overall_score=78,
        skill_scores={"Python": 85, "FastAPI": 75},
        summary="The candidate demonstrated good backend knowledge.",
        strengths=["Strong Python knowledge"],
        areas_for_improvement=[
            "Needs greater technical depth in FastAPI"
        ],
        recommendation=(
            "The candidate demonstrates good potential for the role."
        ),
    )


# --------------------------------------------------------------------------
# CandidateReportRepository.save
# --------------------------------------------------------------------------


def test_save_persists_only_the_reports_own_columns():
    db = MagicMock()
    repository = CandidateReportRepository(db)

    saved = repository.save(_report())

    assert saved.candidate_evaluation_id == 1
    assert saved.summary == (
        "The candidate demonstrated good backend knowledge."
    )
    assert saved.strengths == ["Strong Python knowledge"]
    assert saved.areas_for_improvement == [
        "Needs greater technical depth in FastAPI"
    ]
    assert saved.recommendation == (
        "The candidate demonstrates good potential for the role."
    )

    # interview_id, overall_score, and skill_scores must never reach the
    # candidate_reports table - they are not columns on the model.
    assert not hasattr(saved, "interview_id")
    assert not hasattr(saved, "overall_score")
    assert not hasattr(saved, "skill_scores")

    db.add.assert_called_once_with(saved)
    db.commit.assert_called_once()
    db.refresh.assert_called_once_with(saved)
    db.rollback.assert_not_called()


def test_save_rolls_back_on_failure():
    db = MagicMock()
    db.commit.side_effect = RuntimeError("db is down")

    repository = CandidateReportRepository(db)

    try:
        repository.save(_report())
        assert False, "expected RuntimeError to propagate"
    except RuntimeError:
        pass

    db.rollback.assert_called_once()
    db.refresh.assert_not_called()


# --------------------------------------------------------------------------
# CandidateReportRepository.get_by_candidate_evaluation_id
# --------------------------------------------------------------------------


def test_get_by_candidate_evaluation_id_found():
    db = MagicMock()
    expected = object()
    db.scalar.return_value = expected

    repository = CandidateReportRepository(db)

    assert repository.get_by_candidate_evaluation_id(1) is expected
    db.scalar.assert_called_once()


def test_get_by_candidate_evaluation_id_not_found():
    db = MagicMock()
    db.scalar.return_value = None

    repository = CandidateReportRepository(db)

    assert repository.get_by_candidate_evaluation_id(999) is None


# --------------------------------------------------------------------------
# CandidateRepository / UserRepository
# --------------------------------------------------------------------------


def test_candidate_repository_get_by_id_found():
    db = MagicMock()
    expected = Candidate(id=12, user_id=1)
    db.scalar.return_value = expected

    repository = CandidateRepository(db)

    assert repository.get_by_id(12) is expected


def test_candidate_repository_get_by_id_not_found():
    db = MagicMock()
    db.scalar.return_value = None

    repository = CandidateRepository(db)

    assert repository.get_by_id(999) is None


def test_user_repository_get_by_id_found():
    db = MagicMock()
    expected = User(id=1, first_name="Ahmad", last_name="Khalil")
    db.scalar.return_value = expected

    repository = UserRepository(db)

    assert repository.get_by_id(1) is expected


def test_user_repository_get_by_id_not_found():
    db = MagicMock()
    db.scalar.return_value = None

    repository = UserRepository(db)

    assert repository.get_by_id(999) is None
