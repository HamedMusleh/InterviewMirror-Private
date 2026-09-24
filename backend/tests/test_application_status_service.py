from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.application_service import JobOpportunityNotFoundError
from app.services.application_status_service import ApplicationStatusService

JOB_ID = "JD-TEST"
JOB_OPPORTUNITY_PK = 10
CANDIDATE_ID = 1
USER_ID = 5
APPLICATION_ID = 100
EMAIL = "lara@email.com"


def _build_service(
    *,
    job_opportunity=SimpleNamespace(id=JOB_OPPORTUNITY_PK),
    screening_criteria=SimpleNamespace(id=55),
    user=SimpleNamespace(id=USER_ID),
    candidate=SimpleNamespace(id=CANDIDATE_ID),
    application=SimpleNamespace(id=APPLICATION_ID),
    screening_result=None,
    interview=None,
):
    job_opportunity_repository = MagicMock()
    job_opportunity_repository.get_by_job_id.return_value = job_opportunity

    screening_criteria_repository = MagicMock()
    screening_criteria_repository.get_by_job_opportunity_id.return_value = (
        screening_criteria
    )

    user_repository = MagicMock()
    user_repository.get_by_email.return_value = user

    candidate_repository = MagicMock()
    candidate_repository.get_by_user_id.return_value = candidate

    application_repository = MagicMock()
    application_repository.get_by_candidate_and_job.return_value = (
        application
    )

    screening_repository = MagicMock()
    screening_repository.get_by_application_id.return_value = (
        screening_result
    )

    interview_repository = MagicMock()
    interview_repository.get_by_application_id.return_value = interview

    service = ApplicationStatusService(
        job_opportunity_repository=job_opportunity_repository,
        screening_criteria_repository=screening_criteria_repository,
        user_repository=user_repository,
        candidate_repository=candidate_repository,
        application_repository=application_repository,
        screening_repository=screening_repository,
        interview_repository=interview_repository,
    )

    return service, {
        "job_opportunity_repository": job_opportunity_repository,
        "screening_criteria_repository": screening_criteria_repository,
        "user_repository": user_repository,
        "candidate_repository": candidate_repository,
        "application_repository": application_repository,
        "screening_repository": screening_repository,
        "interview_repository": interview_repository,
    }


def test_missing_job_raises_not_found():
    service, _ = _build_service(job_opportunity=None)

    with pytest.raises(JobOpportunityNotFoundError):
        service.get_status(job_id=JOB_ID, email=EMAIL)


def test_job_without_screening_criteria_is_job_not_ready():
    """Task 1's counterpart on the status side: an unready job reports
    job_not_ready regardless of whether an email is provided."""
    service, mocks = _build_service(screening_criteria=None)

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "job_not_ready"
    assert result.application_id is None
    assert result.interview_id is None
    # No candidate lookups were needed to answer this.
    mocks["user_repository"].get_by_email.assert_not_called()


def test_job_ready_with_no_email_is_can_apply():
    """A first-time visitor with nothing in browser storage yet."""
    service, mocks = _build_service()

    result = service.get_status(job_id=JOB_ID, email=None)

    assert result.state == "can_apply"
    mocks["user_repository"].get_by_email.assert_not_called()


def test_job_ready_with_blank_email_is_can_apply():
    service, mocks = _build_service()

    result = service.get_status(job_id=JOB_ID, email="   ")

    assert result.state == "can_apply"
    mocks["user_repository"].get_by_email.assert_not_called()


def test_unknown_email_is_can_apply():
    service, _ = _build_service(user=None)

    result = service.get_status(job_id=JOB_ID, email="nobody@email.com")

    assert result.state == "can_apply"


def test_email_with_no_linked_candidate_is_can_apply():
    service, _ = _build_service(candidate=None)

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "can_apply"


def test_candidate_with_no_application_for_this_job_is_can_apply():
    service, mocks = _build_service(application=None)

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "can_apply"
    mocks[
        "application_repository"
    ].get_by_candidate_and_job.assert_called_once_with(
        candidate_id=CANDIDATE_ID,
        job_opportunity_id=JOB_OPPORTUNITY_PK,
    )


def test_application_with_no_screening_result_yet_is_screening_in_progress():
    """Task 2: while matching/screening haven't produced a result yet,
    the candidate must not be allowed to resubmit."""
    service, _ = _build_service(screening_result=None)

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "screening_in_progress"
    assert result.application_id == APPLICATION_ID
    assert result.interview_id is None


def test_not_recommended_screening_is_rejected():
    service, _ = _build_service(
        screening_result=SimpleNamespace(final_status="not_recommended")
    )

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "rejected"
    assert result.application_id == APPLICATION_ID
    assert result.interview_id is None


def test_recommended_with_no_interview_yet_is_approved_without_id():
    """The Join Interview button must never be shown with a fabricated
    id -- if InterviewCreationService hasn't produced a real Interview
    row yet, interview_id stays None even though the candidate passed."""
    service, _ = _build_service(
        screening_result=SimpleNamespace(final_status="recommended"),
        interview=None,
    )

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "approved_for_interview"
    assert result.interview_id is None


def test_recommended_with_scheduled_interview_is_approved_with_id():
    service, _ = _build_service(
        screening_result=SimpleNamespace(final_status="recommended"),
        interview=SimpleNamespace(id=777, status="scheduled"),
    )

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "approved_for_interview"
    assert result.application_id == APPLICATION_ID
    assert result.interview_id == 777


def test_completed_interview_is_evaluation_in_progress():
    """Task 4: once the interview is completed, no matter whether a
    CandidateEvaluation row exists yet, the candidate sees the
    evaluation message -- never the form, never Join Interview again."""
    service, _ = _build_service(
        screening_result=SimpleNamespace(final_status="recommended"),
        interview=SimpleNamespace(id=777, status="completed"),
    )

    result = service.get_status(job_id=JOB_ID, email=EMAIL)

    assert result.state == "evaluation_in_progress"
    assert result.application_id == APPLICATION_ID
    assert result.interview_id == 777


def test_email_is_stripped_before_lookup():
    service, mocks = _build_service()

    service.get_status(job_id=JOB_ID, email="  lara@email.com  ")

    mocks["user_repository"].get_by_email.assert_called_once_with(
        "lara@email.com"
    )
