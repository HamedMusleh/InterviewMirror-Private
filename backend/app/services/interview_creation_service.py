from dataclasses import dataclass
from datetime import datetime, timezone

from app.database.models.interview import Interview
from app.modules.screening.repository import ScreeningResultRepository
from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository


RECOMMENDED_SCREENING_STATUS = "recommended"
SCHEDULED_INTERVIEW_STATUS = "scheduled"


class InterviewCreationError(Exception):
    """Base error for expected interview-creation failures."""


class ApplicationNotFoundError(InterviewCreationError):
    """Raised when the requested application does not exist."""


class ScreeningResultNotFoundError(InterviewCreationError):
    """Raised when an application has not completed screening."""


class ApplicationNotRecommendedError(InterviewCreationError):
    """Raised when an application did not pass screening."""


@dataclass(frozen=True)
class InterviewCreationResult:
    interview: Interview
    created: bool


class InterviewCreationService:
    def __init__(
        self,
        application_repository: ApplicationRepository,
        screening_repository: ScreeningResultRepository,
        interview_repository: InterviewRepository,
    ):
        self.application_repository = application_repository
        self.screening_repository = screening_repository
        self.interview_repository = interview_repository

    def create_for_application(
        self,
        application_id: int,
        scheduled_at: datetime | None = None,
    ) -> InterviewCreationResult:
        application = self.application_repository.get_by_id(application_id)

        if application is None:
            raise ApplicationNotFoundError(
                f"Application {application_id} does not exist."
            )

        screening_result = self.screening_repository.get_by_application_id(
            application_id
        )

        if screening_result is None:
            raise ScreeningResultNotFoundError(
                f"Application {application_id} has not been screened."
            )

        if screening_result.final_status != RECOMMENDED_SCREENING_STATUS:
            raise ApplicationNotRecommendedError(
                f"Application {application_id} was not recommended "
                "for an interview."
            )

        existing_interview = (
            self.interview_repository.get_by_application_id(application_id)
        )

        if existing_interview is not None:
            return InterviewCreationResult(
                interview=existing_interview,
                created=False,
            )

        interview = self.interview_repository.create(
            application_id=application_id,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
            status=SCHEDULED_INTERVIEW_STATUS,
        )

        return InterviewCreationResult(
            interview=interview,
            created=True,
        )
