from datetime import datetime

from pydantic import BaseModel


class ApplicationSubmitResponse(BaseModel):
    """Returned after an application (with resume) is stored successfully.

    application_id and resume_id are returned because the frontend needs
    them for API bookkeeping (they are not the same thing as candidate_id,
    which is never returned or accepted from the candidate-facing UI).
    """

    application_id: int
    job_opportunity_id: int
    resume_id: int
    status: str
    applied_at: datetime
    # Only set when this submission's screening result was
    # "recommended" and an Interview record therefore now exists for
    # it (see ApplicationService.submit_application). None otherwise
    # -- the frontend does not fabricate an interview id from this.
    interview_id: int | None = None
