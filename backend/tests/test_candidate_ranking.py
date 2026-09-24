from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import DateTime, Float, Integer

from app.database.models.application import Application
from app.database.models.candidate_ranking import CandidateRanking
from app.database.models.interview import Interview
from app.schemas.candidate_ranking import (
    CandidateRankingEntry,
    CandidateRankingListResponse,
    CandidateRankingRequest,
    RankedCandidate,
)


def test_candidate_rankings_table_matches_the_agreed_schema():
    table = CandidateRanking.__table__

    assert table.name == "candidate_rankings"

    assert isinstance(table.c.id.type, Integer)
    assert isinstance(table.c.job_opportunity_id.type, Integer)
    assert isinstance(table.c.application_id.type, Integer)
    assert isinstance(table.c.interview_id.type, Integer)
    assert isinstance(table.c.overall_score.type, Float)
    assert isinstance(table.c.rank.type, Integer)
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True

    assert table.c.job_opportunity_id.nullable is False
    assert table.c.application_id.nullable is False
    assert table.c.interview_id.nullable is False
    assert table.c.overall_score.nullable is False
    assert table.c.rank.nullable is False
    assert table.c.created_at.nullable is False

    assert table.c.job_opportunity_id.index is not True
    assert table.c.application_id.index is True
    assert table.c.interview_id.index is True


def test_candidate_rankings_table_references_the_expected_tables():
    table = CandidateRanking.__table__

    def targets(column):
        return {
            str(foreign_key.target_fullname)
            for foreign_key in column.foreign_keys
        }

    assert targets(table.c.job_opportunity_id) == {
        "applications.job_opportunity_id",
        "job_opportunities.id",
    }
    assert targets(table.c.application_id) == {
        "applications.id",
        "interviews.application_id",
    }
    assert targets(table.c.interview_id) == {"interviews.id"}


def test_candidate_rankings_table_declares_its_invariants():
    constraint_names = {
        constraint.name
        for constraint in CandidateRanking.__table__.constraints
    }

    assert "uq_candidate_rankings_job_application" in constraint_names
    assert "uq_candidate_rankings_job_rank" in constraint_names
    assert "ck_candidate_rankings_overall_score" in constraint_names
    assert "ck_candidate_rankings_rank" in constraint_names
    assert "fk_candidate_rankings_application_job" in constraint_names
    assert (
        "fk_candidate_rankings_interview_application" in constraint_names
    )

    application_constraint_names = {
        constraint.name for constraint in Application.__table__.constraints
    }
    interview_constraint_names = {
        constraint.name for constraint in Interview.__table__.constraints
    }

    assert (
        "uq_applications_id_job_opportunity" in application_constraint_names
    )
    assert "uq_interviews_id_application" in interview_constraint_names


def test_ranking_entry_accepts_a_valid_payload():
    entry = CandidateRankingEntry(
        application_id=7,
        interview_id=3,
        overall_score=82.5,
    )

    assert entry.application_id == 7
    assert entry.interview_id == 3
    assert entry.overall_score == 82.5


@pytest.mark.parametrize("score", [-0.1, 100.1])
def test_ranking_entry_rejects_scores_outside_the_zero_to_hundred_scale(score):
    with pytest.raises(ValidationError):
        CandidateRankingEntry(
            application_id=7,
            interview_id=3,
            overall_score=score,
        )


@pytest.mark.parametrize(
    "application_id, interview_id",
    [(0, 3), (-1, 3), (7, 0), (7, -1)],
)
def test_ranking_entry_rejects_non_positive_identifiers(
    application_id,
    interview_id,
):
    with pytest.raises(ValidationError):
        CandidateRankingEntry(
            application_id=application_id,
            interview_id=interview_id,
            overall_score=50,
        )


def test_ranking_entry_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        CandidateRankingEntry(
            application_id=7,
            interview_id=3,
            overall_score=50,
            rank=1,
        )


def test_ranking_request_accepts_an_empty_list_to_clear_stored_rankings():
    request = CandidateRankingRequest(rankings=[])

    assert request.rankings == []


def test_ranked_candidate_rejects_a_rank_below_one():
    with pytest.raises(ValidationError):
        RankedCandidate(
            rank=0,
            candidate_id=1,
            candidate_name="Dana Khoury",
            candidate_email="dana@example.com",
            application_id=7,
            interview_id=3,
            overall_score=82.5,
            created_at=datetime.now(timezone.utc),
        )


def test_ranked_candidate_rejects_a_blank_name():
    with pytest.raises(ValidationError):
        RankedCandidate(
            rank=1,
            candidate_id=1,
            candidate_name="   ",
            candidate_email="dana@example.com",
            application_id=7,
            interview_id=3,
            overall_score=82.5,
            created_at=datetime.now(timezone.utc),
        )


def test_response_allows_a_job_opportunity_that_has_no_rankings_yet():
    response = CandidateRankingListResponse(
        job_opportunity_id=1,
        rankings=[],
    )

    assert response.rankings == []
