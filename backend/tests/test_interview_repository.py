"""
Tests for InterviewRepository. `get_application_ids_by_ids` is tested
against an in-memory SQLite database containing only the ``interviews``
table -- see the module docstring of tests/test_application_repository.py
for why the fixture is local. `update_status` is tested with a mocked
session, matching the rest of this repository layer's test style.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.models.interview import Interview
from app.repositories.interview_repository import InterviewRepository


def test_update_status_sets_status_and_flushes():
    interview = SimpleNamespace(id=4, status="in_progress")

    db = MagicMock()
    db.scalar.return_value = interview

    repository = InterviewRepository(db)
    repository.update_status(4, "completed")

    assert interview.status == "completed"
    db.flush.assert_called_once()


def test_update_status_raises_when_interview_not_found():
    db = MagicMock()
    db.scalar.return_value = None

    repository = InterviewRepository(db)

    with pytest.raises(ValueError, match="Interview 4 not found"):
        repository.update_status(4, "completed")


def test_create_adds_flushes_and_refreshes_the_interview():
    db = MagicMock()
    repository = InterviewRepository(db)
    scheduled_at = datetime(2026, 9, 3, 10, 0, tzinfo=timezone.utc)

    interview = repository.create(
        application_id=7,
        scheduled_at=scheduled_at,
        status="scheduled",
    )

    assert interview.application_id == 7
    assert interview.scheduled_at == scheduled_at
    assert interview.status == "scheduled"
    db.add.assert_called_once_with(interview)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(interview)


def test_get_by_application_id_returns_the_first_interview():
    expected = SimpleNamespace(id=12, application_id=7)
    db = MagicMock()
    db.scalar.return_value = expected

    result = InterviewRepository(db).get_by_application_id(7)

    assert result is expected
    statement = db.scalar.call_args.args[0]
    assert "interviews.application_id" in str(statement)
    assert "ORDER BY interviews.id" in str(statement)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    Interview.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()


def _create_interview(
    db_session,
    interview_id: int,
    application_id: int,
) -> None:
    now = datetime.now(timezone.utc)

    db_session.execute(
        Interview.__table__.insert().values(
            id=interview_id,
            application_id=application_id,
            scheduled_at=now,
            status="completed",
            created_at=now,
        )
    )
    db_session.commit()


def test_get_application_ids_by_ids_maps_every_requested_interview(
    db_session,
):
    _create_interview(db_session, interview_id=1, application_id=11)
    _create_interview(db_session, interview_id=2, application_id=22)

    repository = InterviewRepository(db_session)

    assert repository.get_application_ids_by_ids([1, 2]) == {1: 11, 2: 22}


def test_get_application_ids_by_ids_omits_interviews_that_do_not_exist(
    db_session,
):
    _create_interview(db_session, interview_id=1, application_id=11)

    repository = InterviewRepository(db_session)

    assert repository.get_application_ids_by_ids([1, 404]) == {1: 11}


def test_get_application_ids_by_ids_returns_empty_mapping_without_ids(
    db_session,
):
    repository = InterviewRepository(db_session)

    assert repository.get_application_ids_by_ids([]) == {}
