"""
Tests for CandidateRankingRepository against an in-memory SQLite database
containing the tables the ranked-candidate query joins (``user``,
``candidates``, ``applications``, ``interviews`` and
``candidate_rankings``). ``job_opportunities`` is deliberately left out:
it uses Postgres-only JSONB columns and the query never reads it, and
SQLite does not enforce the foreign key pointing at it.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database.models.application import Application
from app.database.models.candidate import Candidate
from app.database.models.candidate_ranking import CandidateRanking
from app.database.models.interview import Interview
from app.database.models.user import User
from app.repositories.candidate_ranking_repository import (
    CandidateRankingRepository,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    for model in (User, Candidate, Application, Interview, CandidateRanking):
        model.__table__.create(engine)

    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()


def _create_candidate(
    db_session,
    candidate_id: int,
    first_name: str,
    last_name: str,
    email: str,
) -> None:
    now = datetime.now(timezone.utc)

    db_session.execute(
        User.__table__.insert().values(
            id=candidate_id,
            email=email,
            password_hash="hashed",
            first_name=first_name,
            last_name=last_name,
            role="candidate",
            created_at=now,
            updated_at=now,
            is_active=True,
        )
    )

    db_session.execute(
        Candidate.__table__.insert().values(
            id=candidate_id,
            user_id=candidate_id,
        )
    )


def _create_application(
    db_session,
    application_id: int,
    candidate_id: int,
    job_opportunity_id: int,
) -> None:
    now = datetime.now(timezone.utc)

    db_session.execute(
        Application.__table__.insert().values(
            id=application_id,
            candidate_id=candidate_id,
            job_opportunity_id=job_opportunity_id,
            status="interviewed",
            applied_at=now,
            updated_at=now,
        )
    )


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


def _seed_candidate_for_job(
    db_session,
    candidate_id: int,
    job_opportunity_id: int,
    first_name: str,
    last_name: str,
    email: str,
) -> None:
    """Create a user/candidate/application/interview chain, all sharing an id."""

    _create_candidate(
        db_session,
        candidate_id=candidate_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    _create_application(
        db_session,
        application_id=candidate_id,
        candidate_id=candidate_id,
        job_opportunity_id=job_opportunity_id,
    )
    _create_interview(
        db_session,
        interview_id=candidate_id,
        application_id=candidate_id,
    )
    db_session.commit()


def _ranking(
    job_opportunity_id: int,
    application_id: int,
    interview_id: int,
    overall_score: float,
    rank: int,
) -> CandidateRanking:
    return CandidateRanking(
        job_opportunity_id=job_opportunity_id,
        application_id=application_id,
        interview_id=interview_id,
        overall_score=overall_score,
        rank=rank,
        created_at=datetime.now(timezone.utc),
    )


def test_create_many_persists_every_ranking(db_session):
    _seed_candidate_for_job(db_session, 1, 10, "Dana", "Khoury", "d@a.com")
    _seed_candidate_for_job(db_session, 2, 10, "Omar", "Nasser", "o@a.com")

    repository = CandidateRankingRepository(db_session)

    created = repository.create_many(
        [
            _ranking(10, 1, 1, 91.0, 1),
            _ranking(10, 2, 2, 74.5, 2),
        ]
    )

    assert [ranking.id for ranking in created] == [1, 2]

    stored = db_session.scalars(select(CandidateRanking)).all()

    assert len(stored) == 2


def test_get_ranked_returns_candidate_identity_in_rank_order(db_session):
    _seed_candidate_for_job(db_session, 1, 10, "Dana", "Khoury", "d@a.com")
    _seed_candidate_for_job(db_session, 2, 10, "Omar", "Nasser", "o@a.com")

    repository = CandidateRankingRepository(db_session)

    repository.create_many(
        [
            _ranking(10, 2, 2, 74.5, 2),
            _ranking(10, 1, 1, 91.0, 1),
        ]
    )

    rows = repository.get_ranked_by_job_opportunity_id(10)

    assert [row.rank for row in rows] == [1, 2]
    assert [row.candidate_id for row in rows] == [1, 2]
    assert [row.first_name for row in rows] == ["Dana", "Omar"]
    assert [row.last_name for row in rows] == ["Khoury", "Nasser"]
    assert [row.email for row in rows] == ["d@a.com", "o@a.com"]
    assert [row.overall_score for row in rows] == [91.0, 74.5]
    assert [row.interview_id for row in rows] == [1, 2]


def test_get_ranked_excludes_other_job_opportunities(db_session):
    _seed_candidate_for_job(db_session, 1, 10, "Dana", "Khoury", "d@a.com")
    _seed_candidate_for_job(db_session, 2, 99, "Omar", "Nasser", "o@a.com")

    repository = CandidateRankingRepository(db_session)

    repository.create_many(
        [
            _ranking(10, 1, 1, 91.0, 1),
            _ranking(99, 2, 2, 88.0, 1),
        ]
    )

    rows = repository.get_ranked_by_job_opportunity_id(10)

    assert [row.application_id for row in rows] == [1]


def test_get_ranked_returns_nothing_for_an_unranked_job_opportunity(
    db_session,
):
    repository = CandidateRankingRepository(db_session)

    assert repository.get_ranked_by_job_opportunity_id(10) == []


def test_delete_removes_only_the_given_job_opportunitys_rankings(db_session):
    _seed_candidate_for_job(db_session, 1, 10, "Dana", "Khoury", "d@a.com")
    _seed_candidate_for_job(db_session, 2, 99, "Omar", "Nasser", "o@a.com")

    repository = CandidateRankingRepository(db_session)

    repository.create_many(
        [
            _ranking(10, 1, 1, 91.0, 1),
            _ranking(99, 2, 2, 88.0, 1),
        ]
    )

    repository.delete_by_job_opportunity_id(10)

    remaining = db_session.scalars(select(CandidateRanking)).all()

    assert [ranking.job_opportunity_id for ranking in remaining] == [99]
