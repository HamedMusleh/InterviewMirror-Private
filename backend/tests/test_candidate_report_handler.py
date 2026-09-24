"""
Unit tests for CandidateReportHandler, the orchestrator behind the
Candidate Report storage/link/API responsibility.

Mirrors the Mock-based handler-testing style used in
tests/test_screening_criteria_persistence.py for ScreeningCriteriaHandler.
"""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.handlers.candidate_report_handler import (
    CandidateEvaluationNotFoundError,
    CandidateNotFoundError,
    CandidateReportAlreadyExistsError,
    CandidateReportHandler,
    CandidateReportNotFoundError,
    CandidateReportRelationshipError,
    InterviewNotFoundError,
)
from app.schemas.candidate_report import CandidateReport


def _report(**overrides) -> CandidateReport:
    fields = dict(
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
    fields.update(overrides)
    return CandidateReport(**fields)


def _interview(interview_id=4, application_id=100):
    return SimpleNamespace(id=interview_id, application_id=application_id)


def _application(application_id=100, candidate_id=12, job_opportunity_id=200):
    return SimpleNamespace(
        id=application_id,
        candidate_id=candidate_id,
        job_opportunity_id=job_opportunity_id,
    )


def _candidate(candidate_id=12, user_id=1):
    return SimpleNamespace(id=candidate_id, user_id=user_id)


def _user(user_id=1, first_name="Ahmad", last_name="Khalil"):
    return SimpleNamespace(
        id=user_id,
        first_name=first_name,
        last_name=last_name,
    )


def _job(job_id=200, title="Backend Developer"):
    return SimpleNamespace(id=job_id, title=title)


def _candidate_evaluation(evaluation_id=1, interview_id=4):
    return SimpleNamespace(
        id=evaluation_id,
        interview_id=interview_id,
        overall_score=78,
        skill_scores={"Python": 85, "FastAPI": 75},
    )


def _stored_report(report_id=7, candidate_evaluation_id=1, **overrides):
    fields = dict(
        id=report_id,
        candidate_evaluation_id=candidate_evaluation_id,
        summary="The candidate demonstrated good backend knowledge.",
        strengths=["Strong Python knowledge"],
        areas_for_improvement=[
            "Needs greater technical depth in FastAPI"
        ],
        recommendation=(
            "The candidate demonstrates good potential for the role."
        ),
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _make_handler(
    candidate_report_repository=None,
    candidate_evaluation_repository=None,
    interview_repository=None,
    application_repository=None,
    candidate_repository=None,
    user_repository=None,
    job_opportunity_repository=None,
):
    return CandidateReportHandler(
        candidate_report_repository=(
            candidate_report_repository or Mock()
        ),
        candidate_evaluation_repository=(
            candidate_evaluation_repository or Mock()
        ),
        interview_repository=interview_repository or Mock(),
        application_repository=application_repository or Mock(),
        candidate_repository=candidate_repository or Mock(),
        user_repository=user_repository or Mock(),
        job_opportunity_repository=(
            job_opportunity_repository or Mock()
        ),
    )


def _fully_wired_repositories():
    interview_repository = Mock()
    interview_repository.get_by_id.return_value = _interview()

    application_repository = Mock()
    application_repository.get_by_id.return_value = _application()

    candidate_repository = Mock()
    candidate_repository.get_by_id.return_value = _candidate()

    user_repository = Mock()
    user_repository.get_by_id.return_value = _user()

    job_opportunity_repository = Mock()
    job_opportunity_repository.get_by_id.return_value = _job()

    candidate_evaluation_repository = Mock()
    candidate_evaluation_repository.get_by_id.return_value = (
        _candidate_evaluation()
    )
    candidate_evaluation_repository.get_by_interview_id.return_value = (
        _candidate_evaluation()
    )

    return {
        "interview_repository": interview_repository,
        "application_repository": application_repository,
        "candidate_repository": candidate_repository,
        "user_repository": user_repository,
        "job_opportunity_repository": job_opportunity_repository,
        "candidate_evaluation_repository": candidate_evaluation_repository,
    }


# --------------------------------------------------------------------------
# store_report
# --------------------------------------------------------------------------


def test_store_report_saves_and_returns_response():
    repos = _fully_wired_repositories()

    candidate_report_repository = Mock()
    candidate_report_repository.get_by_candidate_evaluation_id.return_value = (
        None
    )
    candidate_report_repository.save.return_value = _stored_report()

    handler = _make_handler(
        candidate_report_repository=candidate_report_repository,
        **repos,
    )

    report = _report()
    result = handler.store_report(4, report)

    candidate_report_repository.save.assert_called_once_with(report)

    assert result.report_id == 7
    assert result.candidate_evaluation_id == 1
    assert result.candidate_id == 12
    assert result.interview_id == 4
    assert result.job_title == "Backend Developer"
    assert result.candidate_name == "Ahmad Khalil"

    # overall_score / skill_scores come from CandidateEvaluation, the
    # single source of truth - not from the request body.
    assert result.overall_score == 78
    assert result.skill_scores == {"Python": 85, "FastAPI": 75}


def test_store_report_rejects_path_body_interview_id_mismatch():
    handler = _make_handler(**_fully_wired_repositories())

    with pytest.raises(CandidateReportRelationshipError):
        handler.store_report(999, _report(interview_id=4))

def test_store_report_rejects_overall_score_mismatch():
    handler = _make_handler(**_fully_wired_repositories())

    report = _report(
        interview_id=4,
        overall_score=50,  # deliberately different from DB evaluation
    )

    with pytest.raises(CandidateReportRelationshipError):
        handler.store_report(4, report)


def test_store_report_rejects_skill_scores_mismatch():
    handler = _make_handler(**_fully_wired_repositories())

    report = _report(
        interview_id=4,
        skill_scores={
            "Python": 20,
            "FastAPI": 30,
        },  # deliberately different from DB evaluation
    )

    with pytest.raises(CandidateReportRelationshipError):
        handler.store_report(4, report)


def test_store_report_rejects_unknown_candidate_evaluation():
    repos = _fully_wired_repositories()
    repos["candidate_evaluation_repository"].get_by_id.return_value = None

    handler = _make_handler(**repos)

    with pytest.raises(CandidateEvaluationNotFoundError):
        handler.store_report(4, _report())


def test_store_report_rejects_candidate_evaluation_interview_mismatch():
    repos = _fully_wired_repositories()
    # This evaluation actually belongs to a different interview than
    # the one in the request path/body.
    repos["candidate_evaluation_repository"].get_by_id.return_value = (
        _candidate_evaluation(evaluation_id=1, interview_id=999)
    )

    handler = _make_handler(**repos)

    with pytest.raises(CandidateReportRelationshipError):
        handler.store_report(4, _report(candidate_evaluation_id=1))


def test_store_report_rejects_duplicate_report_for_evaluation():
    repos = _fully_wired_repositories()

    candidate_report_repository = Mock()
    candidate_report_repository.get_by_candidate_evaluation_id.return_value = (
        _stored_report()
    )

    handler = _make_handler(
        candidate_report_repository=candidate_report_repository,
        **repos,
    )

    with pytest.raises(CandidateReportAlreadyExistsError):
        handler.store_report(4, _report())

    candidate_report_repository.save.assert_not_called()


def test_store_report_rejects_wrong_interview():
    repos = _fully_wired_repositories()
    repos["interview_repository"].get_by_id.return_value = None

    handler = _make_handler(**repos)

    with pytest.raises(InterviewNotFoundError):
        handler.store_report(4, _report())


def test_store_report_rejects_wrong_candidate():
    repos = _fully_wired_repositories()
    repos["candidate_repository"].get_by_id.return_value = None

    handler = _make_handler(**repos)

    with pytest.raises(CandidateNotFoundError):
        handler.store_report(4, _report())


def test_store_report_does_not_save_when_validation_fails():
    repos = _fully_wired_repositories()
    repos["interview_repository"].get_by_id.return_value = None

    candidate_report_repository = Mock()
    candidate_report_repository.get_by_candidate_evaluation_id.return_value = (
        None
    )
    handler = _make_handler(
        candidate_report_repository=candidate_report_repository,
        **repos,
    )

    with pytest.raises(InterviewNotFoundError):
        handler.store_report(4, _report())

    candidate_report_repository.save.assert_not_called()


# --------------------------------------------------------------------------
# get_report
# --------------------------------------------------------------------------


def test_get_report_returns_full_response():
    repos = _fully_wired_repositories()

    candidate_report_repository = Mock()
    candidate_report_repository.get_by_candidate_evaluation_id.return_value = (
        _stored_report()
    )

    handler = _make_handler(
        candidate_report_repository=candidate_report_repository,
        **repos,
    )

    result = handler.get_report(4)

    assert result.report_id == 7
    assert result.candidate_evaluation_id == 1
    assert result.candidate_id == 12
    assert result.interview_id == 4
    assert result.job_title == "Backend Developer"
    assert result.candidate_name == "Ahmad Khalil"
    assert result.overall_score == 78
    assert result.skill_scores == {"Python": 85, "FastAPI": 75}
    assert result.summary == (
        "The candidate demonstrated good backend knowledge."
    )
    assert result.recommendation == (
        "The candidate demonstrates good potential for the role."
    )


def test_get_report_raises_when_interview_missing():
    repos = _fully_wired_repositories()
    repos["interview_repository"].get_by_id.return_value = None

    handler = _make_handler(**repos)

    with pytest.raises(InterviewNotFoundError):
        handler.get_report(4)


def test_get_report_raises_when_candidate_missing():
    repos = _fully_wired_repositories()
    repos["candidate_repository"].get_by_id.return_value = None

    handler = _make_handler(**repos)

    with pytest.raises(CandidateNotFoundError):
        handler.get_report(4)


def test_get_report_raises_when_evaluation_not_ready():
    repos = _fully_wired_repositories()
    repos[
        "candidate_evaluation_repository"
    ].get_by_interview_id.return_value = None

    handler = _make_handler(**repos)

    with pytest.raises(CandidateEvaluationNotFoundError):
        handler.get_report(4)


def test_get_report_raises_when_report_not_stored():
    repos = _fully_wired_repositories()

    candidate_report_repository = Mock()
    candidate_report_repository.get_by_candidate_evaluation_id.return_value = (
        None
    )

    handler = _make_handler(
        candidate_report_repository=candidate_report_repository,
        **repos,
    )

    with pytest.raises(CandidateReportNotFoundError):
        handler.get_report(4)
