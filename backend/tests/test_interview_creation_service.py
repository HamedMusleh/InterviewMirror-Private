from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.interview_creation_service import (
    ApplicationNotFoundError,
    ApplicationNotRecommendedError,
    InterviewCreationService,
    ScreeningResultNotFoundError,
)


def _service(
    *,
    application=SimpleNamespace(id=7),
    screening_result=SimpleNamespace(final_status="recommended"),
    existing_interview=None,
):
    application_repository = MagicMock()
    application_repository.get_by_id.return_value = application

    screening_repository = MagicMock()
    screening_repository.get_by_application_id.return_value = (
        screening_result
    )

    interview_repository = MagicMock()
    interview_repository.get_by_application_id.return_value = (
        existing_interview
    )
    interview_repository.create.return_value = SimpleNamespace(id=31)

    service = InterviewCreationService(
        application_repository=application_repository,
        screening_repository=screening_repository,
        interview_repository=interview_repository,
    )

    return service, interview_repository


def test_recommended_application_creates_a_scheduled_interview():
    service, interview_repository = _service()
    scheduled_at = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)

    result = service.create_for_application(
        application_id=7,
        scheduled_at=scheduled_at,
    )

    assert result.created is True
    assert result.interview.id == 31
    interview_repository.create.assert_called_once_with(
        application_id=7,
        scheduled_at=scheduled_at,
        status="scheduled",
    )


def test_creation_defaults_to_the_current_utc_time():
    service, interview_repository = _service()

    service.create_for_application(application_id=7)

    scheduled_at = interview_repository.create.call_args.kwargs[
        "scheduled_at"
    ]
    assert scheduled_at.tzinfo is timezone.utc


def test_retry_returns_the_existing_interview_without_a_duplicate():
    existing = SimpleNamespace(id=12)
    service, interview_repository = _service(existing_interview=existing)

    result = service.create_for_application(application_id=7)

    assert result.created is False
    assert result.interview is existing
    interview_repository.create.assert_not_called()


def test_unknown_application_is_rejected_before_screening_lookup():
    service, interview_repository = _service(application=None)

    with pytest.raises(
        ApplicationNotFoundError,
        match="Application 7 does not exist",
    ):
        service.create_for_application(application_id=7)

    interview_repository.create.assert_not_called()


def test_application_without_screening_result_is_rejected():
    service, interview_repository = _service(screening_result=None)

    with pytest.raises(
        ScreeningResultNotFoundError,
        match="Application 7 has not been screened",
    ):
        service.create_for_application(application_id=7)

    interview_repository.create.assert_not_called()


def test_not_recommended_application_is_rejected():
    service, interview_repository = _service(
        screening_result=SimpleNamespace(final_status="not_recommended")
    )

    with pytest.raises(
        ApplicationNotRecommendedError,
        match="Application 7 was not recommended",
    ):
        service.create_for_application(application_id=7)

    interview_repository.create.assert_not_called()
