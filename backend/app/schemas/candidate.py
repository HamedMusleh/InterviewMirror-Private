from pydantic import BaseModel


class CandidateInfoResponse(BaseModel):
    """Read-only candidate identity used to prefill the application page.

    Intentionally has no id field: the candidate id is an internal
    database value and is never surfaced to the candidate-facing UI.
    """

    first_name: str
    last_name: str
    phone: str | None = None
