from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import Row

from app.database.models.candidate_ranking import CandidateRanking
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_ranking_repository import (
    CandidateRankingRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.schemas.candidate_ranking import (
    CandidateRankingEntry,
    CandidateRankingListResponse,
    CandidateRankingRequest,
    RankedCandidate,
)


class CandidateRankingServiceError(Exception):
    """Base class for failures raised by CandidateRankingService."""


class JobOpportunityNotFoundError(CandidateRankingServiceError):
    """Raised when job_opportunity_id does not refer to an existing job."""


class InvalidRankingEntryError(CandidateRankingServiceError):
    """Raised when a submitted entry does not fit the job opportunity.

    Covers the three ways a syntactically valid request can still be
    inconsistent with what is stored: the same application submitted
    twice, an application that belongs to a different job opportunity,
    and an interview that belongs to a different application.
    """


class CandidateRankingService:
    """Store and retrieve the ranked candidate list of a job opportunity."""

    def __init__(
        self,
        ranking_repository: CandidateRankingRepository,
        application_repository: ApplicationRepository,
        interview_repository: InterviewRepository,
        job_opportunity_repository: JobOpportunityRepository,
    ):
        self.ranking_repository = ranking_repository
        self.application_repository = application_repository
        self.interview_repository = interview_repository
        self.job_opportunity_repository = job_opportunity_repository

    def get_ranked_candidates(
        self,
        job_opportunity_id: int,
    ) -> CandidateRankingListResponse:
        """
        Return the stored ranked candidate list of a job opportunity.

        A job opportunity that exists but has not been ranked yet gets an
        empty list rather than an error - "not ranked yet" is a normal
        state, not a failure.
        """

        self._ensure_job_opportunity_exists(job_opportunity_id)

        return self._build_response(job_opportunity_id)

    def replace_rankings(
        self,
        job_opportunity_id: int,
        request: CandidateRankingRequest,
    ) -> CandidateRankingListResponse:
        """
        Replace the ranked candidate list of a job opportunity.

        Ranks are derived here rather than taken from the caller: the
        entries are ordered by descending score and numbered from 1, so
        the stored ranks always agree with the stored scores.
        """

        self._ensure_job_opportunity_exists(
            job_opportunity_id,
            lock_for_update=True,
        )

        self._validate_entries(job_opportunity_id, request.rankings)

        ordered_entries = self._order_by_rank(request.rankings)

        self.ranking_repository.delete_by_job_opportunity_id(
            job_opportunity_id
        )

        created_at = datetime.now(timezone.utc)

        self.ranking_repository.create_many(
            [
                CandidateRanking(
                    job_opportunity_id=job_opportunity_id,
                    application_id=entry.application_id,
                    interview_id=entry.interview_id,
                    overall_score=entry.overall_score,
                    rank=rank,
                    created_at=created_at,
                )
                for rank, entry in enumerate(ordered_entries, start=1)
            ]
        )

        return self._build_response(job_opportunity_id)

    def _ensure_job_opportunity_exists(
        self,
        job_opportunity_id: int,
        *,
        lock_for_update: bool = False,
    ) -> None:
        if lock_for_update:
            job_opportunity = (
                self.job_opportunity_repository.get_by_id_for_update(
                    job_opportunity_id
                )
            )
        else:
            job_opportunity = self.job_opportunity_repository.get_by_id(
                job_opportunity_id
            )

        if job_opportunity is None:
            raise JobOpportunityNotFoundError(
                f"Job opportunity {job_opportunity_id} does not exist."
            )

    def _validate_entries(
        self,
        job_opportunity_id: int,
        entries: list[CandidateRankingEntry],
    ) -> None:
        """Reject entries that do not fit the job opportunity."""

        application_ids = [entry.application_id for entry in entries]

        duplicated_ids = sorted(
            application_id
            for application_id, count in Counter(application_ids).items()
            if count > 1
        )

        if duplicated_ids:
            raise InvalidRankingEntryError(
                "Each application can be ranked only once, but these were "
                f"submitted more than once: {duplicated_ids}."
            )

        known_application_ids = (
            self.application_repository.get_ids_for_job_opportunity(
                job_opportunity_id,
                application_ids,
            )
        )

        unknown_ids = sorted(
            set(application_ids) - known_application_ids
        )

        if unknown_ids:
            raise InvalidRankingEntryError(
                f"Applications {unknown_ids} do not belong to job "
                f"opportunity {job_opportunity_id}."
            )

        application_id_by_interview_id = (
            self.interview_repository.get_application_ids_by_ids(
                [entry.interview_id for entry in entries]
            )
        )

        mismatched_ids = sorted(
            entry.interview_id
            for entry in entries
            if application_id_by_interview_id.get(entry.interview_id)
            != entry.application_id
        )

        if mismatched_ids:
            raise InvalidRankingEntryError(
                f"Interviews {mismatched_ids} do not belong to the "
                "applications they were submitted with."
            )

    @staticmethod
    def _order_by_rank(
        entries: list[CandidateRankingEntry],
    ) -> list[CandidateRankingEntry]:
        """
        Order entries best first, so enumerating them yields the ranks.

        Candidates with equal scores are ordered by application id, which
        keeps the stored list stable across repeated submissions of the
        same data.
        """

        return sorted(
            entries,
            key=lambda entry: (-entry.overall_score, entry.application_id),
        )

    def _build_response(
        self,
        job_opportunity_id: int,
    ) -> CandidateRankingListResponse:
        rows = self.ranking_repository.get_ranked_by_job_opportunity_id(
            job_opportunity_id
        )

        return CandidateRankingListResponse(
            job_opportunity_id=job_opportunity_id,
            rankings=[self._to_ranked_candidate(row) for row in rows],
        )

    @staticmethod
    def _to_ranked_candidate(row: Row) -> RankedCandidate:
        return RankedCandidate(
            rank=row.rank,
            candidate_id=row.candidate_id,
            candidate_name=f"{row.first_name} {row.last_name}",
            candidate_email=row.email,
            application_id=row.application_id,
            interview_id=row.interview_id,
            overall_score=row.overall_score,
            created_at=row.created_at,
        )
