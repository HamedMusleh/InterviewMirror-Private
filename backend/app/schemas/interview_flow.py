from datetime import datetime

from pydantic import BaseModel

from app.schemas.interview_question_storage import InterviewQuestionResponse


class InterviewFlowResult(BaseModel):
    follow_up_generated: bool
    next_question: InterviewQuestionResponse | None
    interview_completed: bool


class InterviewStatusResponse(BaseModel):
    interview_id: int
    status: str
    completed: bool
    next_question: InterviewQuestionResponse | None

    # How many questions already have a stored answer.
    #
    # Progress is deliberately not stored as a column anywhere -- it is
    # derived from the answers that exist -- so the count is computed per
    # request alongside next_question, from the same set.
    answered_count: int = 0

    # When the candidate first opened the room, or null if they never have.
    #
    # This is what distinguishes an interview that is being resumed from one
    # that has not begun, which the answer count alone cannot do: a
    # candidate who reloads while still on the first question has answered
    # nothing, but has already been greeted, and should not sit through the
    # greeting a second time.
    started_at: datetime | None = None

    # How long the interview has been running, measured on the server.
    #
    # Sent as a duration rather than left to the browser to work out from
    # started_at, because the browser would have to subtract a server
    # timestamp from its own clock, and the two disagree often enough that a
    # candidate with a skewed clock would see a wrong or negative timer.
    elapsed_seconds: int = 0