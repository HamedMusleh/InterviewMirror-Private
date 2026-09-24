from app.repositories.candidate_repository import CandidateRepository
from app.repositories.user_repository import UserRepository
from app.schemas.candidate import CandidateInfoResponse


class CandidateServiceError(Exception):
    """Base class for failures raised by CandidateService."""


class CandidateNotFoundError(CandidateServiceError):
    """Raised when candidate_id does not refer to an existing candidate."""


class CandidateService:
    def __init__(
        self,
        candidate_repository: CandidateRepository,
        user_repository: UserRepository,
    ):
        self.candidate_repository = candidate_repository
        self.user_repository = user_repository

    def get_candidate_info(self, candidate_id: int) -> CandidateInfoResponse:
        candidate = self.candidate_repository.get_by_id(candidate_id)

        if candidate is None:
            raise CandidateNotFoundError(
                f"Candidate {candidate_id} does not exist."
            )

        user = self.user_repository.get_by_id(candidate.user_id)

        if user is None:
            raise CandidateNotFoundError(
                f"Candidate {candidate_id} does not exist."
            )

        return CandidateInfoResponse(
            first_name=user.first_name,
            last_name=user.last_name,
            phone=candidate.phone,
        )
