from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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


def _row(
    rank: int,
    candidate_id: int,
    first_name: str,
    last_name: str,
    email: str,
    application_id: int,
    interview_id: int,
    overall_score: float,
) -> SimpleNamespace:
    """A stand-in for one row of the ranked-candidate query."""

    return SimpleNamespace(
        rank=rank,
        candidate_id=candidate_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        application_id=application_id,
        interview_id=interview_id,
        overall_score=overall_score,
        created_at=datetime.now(timezone.utc),
    )


def _build_service(
    *,
    job_opportunity=SimpleNamespace(id=JOB_OPPORTUNITY_ID),
    known_application_ids=None,
    application_id_by_interview_id=None,
    rows=(),
):
    ranking_repository = MagicMock()
    ranking_repository.get_ranked_by_job_opportunity_id.return_value = list(
        rows
    )

    application_repository = MagicMock()
    application_repository.get_ids_for_job_opportunity.return_value = (
        set() if known_application_ids is None else known_application_ids
    )

    interview_repository = MagicMock()
    interview_repository.get_application_ids_by_ids.return_value = (
        {}
        if application_id_by_interview_id is None
        else application_id_by_interview_id
    )

    job_opportunity_repository = MagicMock()
    job_opportunity_repository.get_by_id.return_value = job_opportunity
    job_opportunity_repository.get_by_id_for_update.return_value = (
        job_opportunity
    )

    service = CandidateRankingService(
        ranking_repository=ranking_repository,
        application_repository=application_repository,
        interview_repository=interview_repository,
        job_opportunity_repository=job_opportunity_repository,
    )

    return service, ranking_repository


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


def test_get_ranked_candidates_maps_rows_to_the_response_schema():
    service, _ = _build_service(
        rows=[
            _row(1, 1, "Dana", "Khoury", "d@a.com", 1, 1, 91.0),
            _row(2, 2, "Omar", "Nasser", "o@a.com", 2, 2, 74.5),
        ]
    )

    response = service.get_ranked_candidates(JOB_OPPORTUNITY_ID)

    assert response.job_opportunity_id == JOB_OPPORTUNITY_ID
    assert [entry.rank for entry in response.rankings] == [1, 2]
    assert [entry.candidate_name for entry in response.rankings] == [
        "Dana Khoury",
        "Omar Nasser",
    ]
    assert [entry.candidate_email for entry in response.rankings] == [
        "d@a.com",
        "o@a.com",
    ]
    assert [entry.overall_score for entry in response.rankings] == [
        91.0,
        74.5,
    ]


def test_get_ranked_candidates_returns_empty_list_when_not_ranked_yet():
    service, _ = _build_service(rows=[])

    response = service.get_ranked_candidates(JOB_OPPORTUNITY_ID)

    assert response.rankings == []


def test_get_ranked_candidates_raises_when_job_opportunity_is_unknown():
    service, ranking_repository = _build_service(job_opportunity=None)

    with pytest.raises(JobOpportunityNotFoundError, match="10"):
        service.get_ranked_candidates(JOB_OPPORTUNITY_ID)

    ranking_repository.get_ranked_by_job_opportunity_id.assert_not_called()


def test_replace_rankings_numbers_candidates_by_descending_score():
    service, ranking_repository = _build_service(
        known_application_ids={1, 2, 3},
        application_id_by_interview_id={1: 1, 2: 2, 3: 3},
    )

    service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 74.5), (2, 2, 91.0), (3, 3, 60.0)),
    )

    stored = ranking_repository.create_many.call_args.args[0]

    assert [ranking.rank for ranking in stored] == [1, 2, 3]
    assert [ranking.application_id for ranking in stored] == [2, 1, 3]
    assert [ranking.overall_score for ranking in stored] == [91.0, 74.5, 60.0]
    assert {ranking.job_opportunity_id for ranking in stored} == {
        JOB_OPPORTUNITY_ID
    }


def test_replace_rankings_breaks_score_ties_by_application_id():
    service, ranking_repository = _build_service(
        known_application_ids={1, 2},
        application_id_by_interview_id={1: 1, 2: 2},
    )

    service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((2, 2, 80.0), (1, 1, 80.0)),
    )

    stored = ranking_repository.create_many.call_args.args[0]

    assert [ranking.application_id for ranking in stored] == [1, 2]
    assert [ranking.rank for ranking in stored] == [1, 2]


def test_replace_rankings_clears_the_previous_list_before_storing():
    service, ranking_repository = _build_service(
        known_application_ids={1},
        application_id_by_interview_id={1: 1},
    )

    service.replace_rankings(JOB_OPPORTUNITY_ID, _request((1, 1, 80.0)))

    called_methods = [call[0] for call in ranking_repository.mock_calls]

    assert called_methods.index(
        "delete_by_job_opportunity_id"
    ) < called_methods.index("create_many")


def test_replace_rankings_locks_the_job_before_modifying_the_list():
    service, ranking_repository = _build_service(
        known_application_ids={1},
        application_id_by_interview_id={1: 1},
    )

    service.replace_rankings(JOB_OPPORTUNITY_ID, _request((1, 1, 80.0)))

    repository = service.job_opportunity_repository
    repository.get_by_id_for_update.assert_called_once_with(
        JOB_OPPORTUNITY_ID
    )
    repository.get_by_id.assert_not_called()
    ranking_repository.delete_by_job_opportunity_id.assert_called_once_with(
        JOB_OPPORTUNITY_ID
    )


def test_replace_rankings_accepts_an_empty_list_to_clear_storage():
    service, ranking_repository = _build_service(rows=[])

    response = service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        CandidateRankingRequest(rankings=[]),
    )

    ranking_repository.delete_by_job_opportunity_id.assert_called_once_with(
        JOB_OPPORTUNITY_ID
    )
    ranking_repository.create_many.assert_called_once_with([])
    assert response.rankings == []


def test_replace_rankings_returns_the_stored_list():
    service, _ = _build_service(
        known_application_ids={1},
        application_id_by_interview_id={1: 1},
        rows=[_row(1, 1, "Dana", "Khoury", "d@a.com", 1, 1, 80.0)],
    )

    response = service.replace_rankings(
        JOB_OPPORTUNITY_ID,
        _request((1, 1, 80.0)),
    )

    assert [entry.candidate_name for entry in response.rankings] == [
        "Dana Khoury"
    ]


def test_replace_rankings_raises_when_job_opportunity_is_unknown():
    service, ranking_repository = _build_service(job_opportunity=None)

    with pytest.raises(JobOpportunityNotFoundError, match="10"):
        service.replace_rankings(JOB_OPPORTUNITY_ID, _request((1, 1, 80.0)))

    ranking_repository.delete_by_job_opportunity_id.assert_not_called()
    ranking_repository.create_many.assert_not_called()


def test_replace_rankings_rejects_the_same_application_submitted_twice():
    service, ranking_repository = _build_service(
        known_application_ids={1},
        application_id_by_interview_id={1: 1, 2: 1},
    )

    with pytest.raises(InvalidRankingEntryError, match=r"\[1\]"):
        service.replace_rankings(
            JOB_OPPORTUNITY_ID,
            _request((1, 1, 80.0), (1, 2, 70.0)),
        )

    ranking_repository.create_many.assert_not_called()


def test_replace_rankings_rejects_applications_of_another_job_opportunity():
    service, ranking_repository = _build_service(
        known_application_ids={1},
        application_id_by_interview_id={1: 1, 2: 2},
    )

    with pytest.raises(InvalidRankingEntryError, match=r"\[2\]"):
        service.replace_rankings(
            JOB_OPPORTUNITY_ID,
            _request((1, 1, 80.0), (2, 2, 70.0)),
        )

    ranking_repository.delete_by_job_opportunity_id.assert_not_called()
    ranking_repository.create_many.assert_not_called()


def test_replace_rankings_rejects_an_interview_of_another_application():
    service, ranking_repository = _build_service(
        known_application_ids={1, 2},
        application_id_by_interview_id={1: 1, 2: 1},
    )

    with pytest.raises(InvalidRankingEntryError, match=r"\[2\]"):
        service.replace_rankings(
            JOB_OPPORTUNITY_ID,
            _request((1, 1, 80.0), (2, 2, 70.0)),
        )

    ranking_repository.create_many.assert_not_called()


def test_replace_rankings_rejects_an_interview_that_does_not_exist():
    service, ranking_repository = _build_service(
        known_application_ids={1},
        application_id_by_interview_id={},
    )

    with pytest.raises(InvalidRankingEntryError, match=r"\[404\]"):
        service.replace_rankings(
            JOB_OPPORTUNITY_ID,
            _request((1, 404, 80.0)),
        )

    ranking_repository.create_many.assert_not_called()
