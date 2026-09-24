from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.candidate_service import (
    CandidateNotFoundError,
    CandidateService,
)


def _build_service(candidate=None, user=None):
    candidate_repository = MagicMock()
    candidate_repository.get_by_id.return_value = candidate

    user_repository = MagicMock()
    user_repository.get_by_id.return_value = user

    service = CandidateService(
        candidate_repository=candidate_repository,
        user_repository=user_repository,
    )

    return service, candidate_repository, user_repository


def test_get_candidate_info_returns_name_and_phone():
    candidate = SimpleNamespace(id=1, user_id=5, phone="+970-59-000-0000")
    user = SimpleNamespace(id=5, first_name="Lina", last_name="Odeh")

    service, candidate_repository, user_repository = _build_service(
        candidate=candidate, user=user
    )

    info = service.get_candidate_info(1)

    candidate_repository.get_by_id.assert_called_once_with(1)
    user_repository.get_by_id.assert_called_once_with(5)

    assert info.first_name == "Lina"
    assert info.last_name == "Odeh"
    assert info.phone == "+970-59-000-0000"


def test_get_candidate_info_raises_when_candidate_missing():
    service, candidate_repository, user_repository = _build_service(
        candidate=None,
    )

    with pytest.raises(CandidateNotFoundError):
        service.get_candidate_info(1)

    user_repository.get_by_id.assert_not_called()


def test_get_candidate_info_raises_when_user_missing():
    candidate = SimpleNamespace(id=1, user_id=5, phone=None)

    service, candidate_repository, user_repository = _build_service(
        candidate=candidate, user=None
    )

    with pytest.raises(CandidateNotFoundError):
        service.get_candidate_info(1)
