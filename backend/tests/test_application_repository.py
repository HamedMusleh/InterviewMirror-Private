"""
Tests for ApplicationRepository against an in-memory SQLite database
containing only the ``applications`` table. The project has no shared
test-database fixture (see tests/test_screening_criteria_persistence.py),
and the tables ``applications`` references use Postgres-only JSONB
columns, so the fixture is scoped locally to this file. SQLite's foreign
key enforcement is left at its default (off) for the same reason.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.models.application import Application
from app.repositories.application_repository import ApplicationRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    Application.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()


def _create_application(
    db_session,
    application_id: int,
    job_opportunity_id: int,
) -> None:
    now = datetime.now(timezone.utc)

    db_session.execute(
        Application.__table__.insert().values(
            id=application_id,
            candidate_id=application_id,
            job_opportunity_id=job_opportunity_id,
            status="interviewed",
            applied_at=now,
            updated_at=now,
        )
    )
    db_session.commit()


def test_get_ids_for_job_opportunity_keeps_only_the_jobs_own_applications(
    db_session,
):
    _create_application(db_session, application_id=1, job_opportunity_id=10)
    _create_application(db_session, application_id=2, job_opportunity_id=10)
    _create_application(db_session, application_id=3, job_opportunity_id=99)

    repository = ApplicationRepository(db_session)

    assert repository.get_ids_for_job_opportunity(10, [1, 2, 3]) == {1, 2}


def test_get_ids_for_job_opportunity_ignores_unknown_application_ids(
    db_session,
):
    _create_application(db_session, application_id=1, job_opportunity_id=10)

    repository = ApplicationRepository(db_session)

    assert repository.get_ids_for_job_opportunity(10, [1, 404]) == {1}


def test_get_ids_for_job_opportunity_returns_empty_set_without_ids(
    db_session,
):
    repository = ApplicationRepository(db_session)

    assert repository.get_ids_for_job_opportunity(10, []) == set()


def test_create_adds_and_flushes_without_committing(db_session):
    repository = ApplicationRepository(db_session)

    application = repository.create(
        candidate_id=1,
        job_opportunity_id=10,
        status="applied",
    )

    assert application.id is not None
    assert application.candidate_id == 1
    assert application.job_opportunity_id == 10
    assert application.status == "applied"
    assert application.applied_at is not None
    assert application.updated_at is not None

    application_id = application.id

    # The repository should only flush, not commit.
    # Rolling back should therefore remove the new application.
    db_session.rollback()

    assert repository.get_by_id(application_id) is None


def test_create_persists_once_the_caller_commits(db_session):
    repository = ApplicationRepository(db_session)

    application = repository.create(
        candidate_id=1,
        job_opportunity_id=10,
        status="applied",
    )

    db_session.commit()

    fetched = repository.get_by_id(application.id)

    assert fetched is not None
    assert fetched.candidate_id == 1
    assert fetched.job_opportunity_id == 10
    assert fetched.status == "applied"


def test_create_rejects_duplicate_candidate_job_pair_at_the_db_level(
    db_session,
):
    repository = ApplicationRepository(db_session)

    repository.create(
        candidate_id=1,
        job_opportunity_id=10,
        status="applied",
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        repository.create(
            candidate_id=1,
            job_opportunity_id=10,
            status="applied",
        )

    db_session.rollback()


def test_get_by_candidate_and_job_finds_existing_application(db_session):
    _create_application(
        db_session,
        application_id=1,
        job_opportunity_id=10,
    )

    repository = ApplicationRepository(db_session)

    found = repository.get_by_candidate_and_job(
        candidate_id=1,
        job_opportunity_id=10,
    )

    assert found is not None
    assert found.id == 1
    assert found.candidate_id == 1
    assert found.job_opportunity_id == 10


def test_get_by_candidate_and_job_returns_none_when_no_match(db_session):
    _create_application(
        db_session,
        application_id=1,
        job_opportunity_id=10,
    )

    repository = ApplicationRepository(db_session)

    assert (
        repository.get_by_candidate_and_job(
            candidate_id=1,
            job_opportunity_id=999,
        )
        is None
    )

    assert (
        repository.get_by_candidate_and_job(
            candidate_id=999,
            job_opportunity_id=10,
        )
        is None
    )