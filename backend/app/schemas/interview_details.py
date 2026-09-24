from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class InterviewQuestionDetail(BaseModel):
    """
    One question within an interview, combined with its answer (if any)
    and its per-question evaluation breakdown (if evaluated yet).

    score / relevance_score / correctness_score / depth_score /
    practicality_score / strengths / weaknesses are all None/empty when
    no InterviewAnswerEvaluation exists yet for this question's answer -
    e.g. the answer hasn't been evaluated, or there's no answer at all.
    """

    model_config = ConfigDict(extra="forbid")

    question_id: int = Field(gt=0)
    question: NonEmptyString
    skill: str | None = None
    is_follow_up: bool
    parent_question_id: int | None = None

    answer: str | None = None

    score: float | None = None
    relevance_score: int | None = None
    correctness_score: int | None = None
    depth_score: int | None = None
    practicality_score: int | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class InterviewDetailsResponse(BaseModel):
    """
    Response for GET /api/interviews/{interview_id}/details.

    Questions are returned in interview sequence_number order (see
    InterviewQuestionRepository.get_by_interview_id).
    """

    model_config = ConfigDict(extra="forbid")

    interview_id: int = Field(gt=0)
    questions: list[InterviewQuestionDetail]