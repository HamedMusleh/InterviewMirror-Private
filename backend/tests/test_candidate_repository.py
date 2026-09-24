"""
Tests for CandidateRepository against an in-memory SQLite database
containing only the ``candidates`` table. Fixture scoped locally to this
file, the same way tests/test_application_repository.py does it -- see
that file's module docstring for why. Candidate.user_id has a foreign
key to the ``user`` table, but SQLite's foreign key enforcement is left
at its default (off), so the ``user`` table doesn't need to exist here
either.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.models.candidate import Candidate
from app.repositories.candidate_repository import CandidateRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    Candidate.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()


def _create_candidate(
    db_session,
    candidate_id: int,
    user_id: int,
    phone: str | None = None,
) -> None:
    db_session.execute(
        Candidate.__table__.insert().values(
            id=candidate_id,
            user_id=user_id,
            phone=phone,
        )
    )
    db_session.commit()


def test_get_by_user_id_finds_existing_candidate(db_session):
    _create_candidate(db_session, candidate_id=1, user_id=5, phone="0599123456")

    repository = CandidateRepository(db_session)

    found = repository.get_by_user_id(5)

    assert found is not None
    assert found.id == 1
    assert found.user_id == 5
    assert found.phone == "0599123456"


def test_get_by_user_id_returns_none_when_no_match(db_session):
    _create_candidate(db_session, candidate_id=1, user_id=5)

    repository = CandidateRepository(db_session)

    assert repository.get_by_user_id(999) is None


def test_create_adds_and_flushes_without_committing(db_session):
    repository = CandidateRepository(db_session)

    candidate = repository.create(user_id=5, phone="0599123456")

    assert candidate.id is not None
    assert candidate.user_id == 5
    assert candidate.phone == "0599123456"

    candidate_id = candidate.id

    # The repository should only flush, not commit.
    # Rolling back should therefore remove the new candidate.
    db_session.rollback()

    assert repository.get_by_id(candidate_id) is None


def test_create_without_phone_leaves_it_null(db_session):
    repository = CandidateRepository(db_session)

    candidate = repository.create(user_id=5)

    assert candidate.phone is None


def test_create_persists_once_the_caller_commits(db_session):
    repository = CandidateRepository(db_session)

    candidate = repository.create(user_id=5, phone="0599123456")

    db_session.commit()

    fetched = repository.get_by_user_id(5)

    assert fetched is not None
    assert fetched.id == candidate.id
    assert fetched.phone == "0599123456"


def test_create_rejects_a_second_candidate_for_the_same_user_at_the_db_level(
    db_session,
):
    repository = CandidateRepository(db_session)

    repository.create(user_id=5, phone="0599123456")
    db_session.commit()

    with pytest.raises(IntegrityError):
        repository.create(user_id=5, phone="0599999999")

    db_session.rollback()
