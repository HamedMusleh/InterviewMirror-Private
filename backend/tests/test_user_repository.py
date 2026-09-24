"""
Tests for UserRepository against an in-memory SQLite database containing
only the ``users`` table. Fixture scoped locally to this file, the same
way tests/test_application_repository.py does it -- see that file's
module docstring for why.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database.models.user import User
from app.repositories.user_repository import UserRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    User.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()


def _create_user(db_session, user_id: int, email: str) -> None:
    now = datetime.now(timezone.utc)

    db_session.execute(
        User.__table__.insert().values(
            id=user_id,
            email=email,
            password_hash="irrelevant-for-this-test",
            first_name="Existing",
            last_name="User",
            role="candidate",
            created_at=now,
            updated_at=now,
            is_active=True,
        )
    )
    db_session.commit()


def test_get_by_email_finds_existing_user(db_session):
    _create_user(db_session, user_id=1, email="lara@email.com")

    repository = UserRepository(db_session)

    found = repository.get_by_email("lara@email.com")

    assert found is not None
    assert found.id == 1
    assert found.email == "lara@email.com"


def test_get_by_email_returns_none_when_no_match(db_session):
    _create_user(db_session, user_id=1, email="lara@email.com")

    repository = UserRepository(db_session)

    assert repository.get_by_email("nobody@email.com") is None


def test_create_adds_and_flushes_without_committing(db_session):
    repository = UserRepository(db_session)

    user = repository.create(
        email="tasneem@email.com",
        first_name="Tasneem",
        last_name="Odeh",
        password_hash="no-authentication-configured",
        role="candidate",
    )

    assert user.id is not None
    assert user.email == "tasneem@email.com"
    assert user.first_name == "Tasneem"
    assert user.last_name == "Odeh"
    assert user.role == "candidate"

    user_id = user.id

    # The repository should only flush, not commit.
    # Rolling back should therefore remove the new user.
    db_session.rollback()

    assert repository.get_by_id(user_id) is None


def test_create_persists_once_the_caller_commits(db_session):
    repository = UserRepository(db_session)

    user = repository.create(
        email="tasneem@email.com",
        first_name="Tasneem",
        last_name="Odeh",
        password_hash="no-authentication-configured",
        role="candidate",
    )

    db_session.commit()

    fetched = repository.get_by_email("tasneem@email.com")

    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.first_name == "Tasneem"
    assert fetched.last_name == "Odeh"


def test_create_rejects_duplicate_email_at_the_db_level(db_session):
    repository = UserRepository(db_session)

    repository.create(
        email="lara@email.com",
        first_name="Lara",
        last_name="Haddad",
        password_hash="no-authentication-configured",
        role="candidate",
    )
    db_session.commit()

    with pytest.raises(IntegrityError):
        repository.create(
            email="lara@email.com",
            first_name="Someone",
            last_name="Else",
            password_hash="no-authentication-configured",
            role="candidate",
        )

    db_session.rollback()
