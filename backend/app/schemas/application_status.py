from typing import Literal

from pydantic import BaseModel

# Mirrors the JobApplicationPage's derived application-page state on
# the frontend (see frontend/src/services/jobApplicationApi.ts). Kept
# as a single source of truth here since Pydantic validates against
# it on every response.
ApplicationPageState = Literal[
    "job_not_ready",
    "can_apply",
    "screening_in_progress",
    "approved_for_interview",
    "rejected",
    "evaluation_in_progress",
]


class ApplicationStatusResponse(BaseModel):
    """What the candidate-facing JobApplicationPage should render for
    a given job (and, once known, a given returning candidate).

    interview_id is only ever populated for "approved_for_interview",
    and only once a real Interview record exists -- it is never
    fabricated. application_id is included whenever an Application
    already exists, so the frontend never needs to invent one either.
    """

    state: ApplicationPageState
    application_id: int | None = None
    interview_id: int | None = None
