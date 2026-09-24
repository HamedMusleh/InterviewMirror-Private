"""
Integration tests wiring the real CandidateRankingService to the real
repositories over an in-memory SQLite database.

The unit tests around this feature mock one side or the other:
tests/test_candidate_ranking_service.py hand-builds the rows the
repository is expected to return, and tests/test_candidate_ranking_api.py
fakes the service. This file covers what neither can - that storing and
then reading a ranked list actually works end to end, and that replacing
an existing list does not trip the ``uq_candidate_rankings_job_rank``
constraint when two candidates swap places. SQLite enforces UNIQUE
constraints, so that check is real here.

``job_opportunities`` is not created: it uses Postgres-only JSONB columns
that SQLite cannot compile. The job-opportunity repository is therefore
the one collaborator still stubbed, since this feature only ever asks it
whether a job exists.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database.models.application import Application
from app.database.models.candidate import Candidate
from app.database.models.candidate_ranking import CandidateRanking
from app.database.models.interview import Interview
from app.database.models.user import User
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_ranking_repository import (
    CandidateRankingRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.schemas.candidate_ranking import (
    CandidateRankingEntry,
    CandidateRankingRequest,
)
from app.services.candidate_ranking_service import (
    CandidateRankingService,
    InvalidRankingEntryError,
    JobOpportunityNotFoundError,
)


JOB_OPPORTUNITY_ID = 10


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    for model in (User, Candidate, Application, Interview, CandidateRanking):
        model.__table__.create(engine)

    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()

    try:
        yield session
    finally:
        session.close()


def _seed_candidate(
    db_session,
    candidate_id: int,
    first_name: str,
    last_name: str,
    job_opportunity_id: int = JOB_OPPORTUNITY_ID,
) -> None:
    """Create a user/candidate/application/interview chain sharing one id."""

    now = datetime.now(timezone.utc)

    db_session.execute(
        User.__table__.insert().values(
            id=candidate_id,
            email=f"{first_name.lower()}@example.com",
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
    db_session.execute(
        Application.__table__.insert().values(
            id=candidate_id,
            candidate_id=candidate_id,
            job_opportunity_id=job_opportunity_id,
            status="interviewed",
            applied_at=now,
            updated_at=now,
        )
    )
    db_session.execute(
        Interview.__table__.insert().values(
            id=candidate_id,
            application_id=candidate_id,
            scheduled_at=now,
            status="completed",
            created_at=now,
        )
    )
    db_session.commit()


def _build_service(
    db_session,
    job_opportunity_exists: bool = True,
) -> CandidateRankingService:
    job_opportunity_repository = MagicMock()
    job_opportunity_repository.get_by_id.return_value = (
        SimpleNamespace(id=JOB_OPPORTUNITY_ID)
        if job_opportunity_exists
        else None
    )
    job_opportunity_repository.get_by_id_for_update.return_value = (
        job_opportunity_repository.get_by_id.return_value
    )

    return CandidateRankingService(
        ranking_repository=CandidateRankingRepository(db_session),
        application_repository=ApplicationRepository(db_session),
        interview_repository=InterviewRepository(db_session),
        job_opportunity_repository=job_opportunity_repository,
    )


def _request(*entries: tuple[int, int, float]) -> CandidateRankingRequest:
    return CandidateRankingRequest(
        rankings=[
            CandidateRankingEntry(
                application_id=application_id,
                interview_id=interview_id,
                overall_score=overall_score,
            )
            for application_id, interview_id, overall_score in entries
        ]
    )


def test_stored_rankings_can_be_read_back_with_candidate_identity(db_session):
    _seed_candidate(db_session, 1, "Dana", "Khoury")
    _seed_candidate(db_session, 2, "Omar", "Nasser")

    service = _build_service(db_session)

    service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 74.5), (2, 2, 91.0)),
    )

    response = service.get_ranked_candidates(JOB_OPPORTUNITY_ID)

    assert [entry.rank for entry in response.rankings] == [1, 2]
    assert [entry.candidate_name for entry in response.rankings] == [
        "Omar Nasser",
        "Dana Khoury",
    ]
    assert [entry.candidate_email for entry in response.rankings] == [
        "omar@example.com",
        "dana@example.com",
    ]
    assert [entry.overall_score for entry in response.rankings] == [91.0, 74.5]


def test_replacing_a_list_lets_two_candidates_swap_ranks(db_session):
    _seed_candidate(db_session, 1, "Dana", "Khoury")
    _seed_candidate(db_session, 2, "Omar", "Nasser")

    service = _build_service(db_session)

    service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 91.0), (2, 2, 74.5)),
    )

    # Re-scored the other way round: rank 1 and rank 2 change hands, which
    # only works because the previous list is deleted before the new rows
    # are inserted.
    response = service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 74.5), (2, 2, 91.0)),
    )

    assert [entry.application_id for entry in response.rankings] == [2, 1]
    assert [entry.rank for entry in response.rankings] == [1, 2]

    stored = db_session.scalars(select(CandidateRanking)).all()

    assert len(stored) == 2


def test_replacing_a_list_drops_candidates_left_out_of_the_new_one(
    db_session,
):
    _seed_candidate(db_session, 1, "Dana", "Khoury")
    _seed_candidate(db_session, 2, "Omar", "Nasser")

    service = _build_service(db_session)

    service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 91.0), (2, 2, 74.5)),
    )

    response = service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 91.0)),
    )

    assert [entry.application_id for entry in response.rankings] == [1]
    assert len(db_session.scalars(select(CandidateRanking)).all()) == 1


def test_replacing_a_list_with_empty_rankings_clears_it(db_session):
    _seed_candidate(db_session, 1, "Dana", "Khoury")

    service = _build_service(db_session)

    service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 91.0)),
    )

    response = service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        CandidateRankingRequest(rankings=[]),
    )

    assert response.rankings == []
    assert db_session.scalars(select(CandidateRanking)).all() == []


def test_rankings_of_another_job_opportunity_are_left_alone(db_session):
    _seed_candidate(db_session, 1, "Dana", "Khoury")
    _seed_candidate(db_session, 2, "Omar", "Nasser", job_opportunity_id=99)

    service = _build_service(db_session)

    CandidateRankingRepository(db_session).create_many(
        [
            CandidateRanking(
                job_opportunity_id=99,
                application_id=2,
                interview_id=2,
                overall_score=88.0,
                rank=1,
                created_at=datetime.now(timezone.utc),
            )
        ]
    )

    service.replace_rankings(JOB_OPPORTUNITY_ID, _request((1, 1, 91.0)))

    stored = db_session.scalars(
        select(CandidateRanking).order_by(CandidateRanking.job_opportunity_id)
    ).all()

    assert [ranking.job_opportunity_id for ranking in stored] == [
        JOB_OPPORTUNITY_ID,
        99,
    ]


def test_an_application_from_another_job_opportunity_is_rejected(db_session):
    _seed_candidate(db_session, 1, "Dana", "Khoury")
    _seed_candidate(db_session, 2, "Omar", "Nasser", job_opportunity_id=99)

    service = _build_service(db_session)

    with pytest.raises(InvalidRankingEntryError, match=r"\[2\]"):
        service.replace_rankings(
            JOB_OPPORTUNITY_ID,
            _request((1, 1, 91.0), (2, 2, 74.5)),
        )

    assert db_session.scalars(select(CandidateRanking)).all() == []


def test_an_interview_from_another_application_is_rejected(db_session):
    _seed_candidate(db_session, 1, "Dana", "Khoury")
    _seed_candidate(db_session, 2, "Omar", "Nasser")

    service = _build_service(db_session)

    with pytest.raises(InvalidRankingEntryError, match=r"\[2\]"):
        service.replace_rankings(
            JOB_OPPORTUNITY_ID,
            _request((1, 2, 91.0)),
        )

    assert db_session.scalars(select(CandidateRanking)).all() == []


def test_an_unknown_job_opportunity_is_rejected_before_touching_storage(
    db_session,
):
    _seed_candidate(db_session, 1, "Dana", "Khoury")

    service = _build_service(db_session, job_opportunity_exists=False)

    with pytest.raises(JobOpportunityNotFoundError):
        service.replace_rankings(JOB_OPPORTUNITY_ID, _request((1, 1, 91.0)))

    assert db_session.scalars(select(CandidateRanking)).all() == []


def test_a_job_opportunity_without_rankings_returns_an_empty_list(db_session):
    service = _build_service(db_session)

    response = service.get_ranked_candidates(JOB_OPPORTUNITY_ID)

    assert response.job_opportunity_id == JOB_OPPORTUNITY_ID
    assert response.rankings == []
