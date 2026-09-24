from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
    ),
]


# All evaluation scores use a 1-10 scale.
Score = Annotated[
    float,
    Field(ge=1, le=10),
]


class EvaluationInput(BaseModel):
    """
    Input for the evaluation component.

    Contains the original interview answer together with the
    structured analysis produced by the Answer Analysis component.
    """

    model_config = ConfigDict(extra="forbid")

    answer_id: int = Field(gt=0)
    question_id: int = Field(gt=0)
    question: NonEmptyString
    skill: NonEmptyString | None = None

    answer: NonEmptyString

    answer_quality: Literal["low", "medium", "high"]

    relevant_points: list[NonEmptyString] = Field(
        default_factory=list
    )

    missing_areas: list[NonEmptyString] = Field(
        default_factory=list
    )

    evidence: list[NonEmptyString] = Field(
        default_factory=list
    )


class CriteriaScores(BaseModel):
    """
    Numeric scores assigned independently by the Evaluation LLM.

    The LLM scores each evaluation criterion separately.
    The final weighted score is calculated by the scoring service.

    All criterion scores use a 1-10 scale.
    """

    model_config = ConfigDict(extra="forbid")

    relevance: float = Field(ge=1, le=10)
    correctness: float = Field(ge=1, le=10)
    depth: float = Field(ge=1, le=10)
    practicality: float = Field(ge=1, le=10)


class EvaluationResult(BaseModel):
    """
    Raw evaluation result produced by the Evaluation LLM.

    This schema does not contain the final weighted score.
    """

    model_config = ConfigDict(extra="forbid")

    criteria_scores: CriteriaScores

    strengths: list[NonEmptyString] = Field(
        default_factory=list
    )

    weaknesses: list[NonEmptyString] = Field(
        default_factory=list
    )


class FinalEvaluationResult(BaseModel):
    """
    Final evaluation result after deterministic score calculation.

    The criterion scores, strengths, and weaknesses originate
    from the Evaluation LLM.

    The final score is calculated by EvaluationScoringService
    using the configured evaluation weights.

    All scores use a 1-10 scale.
    """

    model_config = ConfigDict(extra="forbid")

    criteria_scores: CriteriaScores

    strengths: list[NonEmptyString] = Field(
        default_factory=list
    )

    weaknesses: list[NonEmptyString] = Field(
        default_factory=list
    )

    score: float = Field(ge=1, le=10)


class InterviewAnswerEvaluationCreate(BaseModel):
    """
    Input for storing the evaluation of a single interview answer.

    All scores use a 1-10 scale.
    """

    model_config = ConfigDict(extra="forbid")

    answer_id: int = Field(gt=0)

    relevance_score: int = Field(ge=1, le=10)
    correctness_score: int = Field(ge=1, le=10)
    depth_score: int = Field(ge=1, le=10)
    practicality_score: int = Field(ge=1, le=10)

    strengths: list[NonEmptyString] = Field(
        default_factory=list
    )

    weaknesses: list[NonEmptyString] = Field(
        default_factory=list
    )

    score: float = Field(ge=1, le=10)


class InterviewAnswerEvaluationResponse(BaseModel):
    """
    Evaluation response for a single interview answer.

    All scores use a 1-10 scale.
    """

    model_config = ConfigDict(from_attributes=True)

    answer_id: int
    skill: str | None

    relevance_score: int
    correctness_score: int
    depth_score: int
    practicality_score: int

    strengths: list[str]
    weaknesses: list[str]

    score: float


class InterviewEvaluationsResponse(BaseModel):
    interview_id: int
    candidate_id: int
    evaluations: list[InterviewAnswerEvaluationResponse]


class SkillScore(BaseModel):
    """
    Average score for a specific skill.

    Candidate-level skill scores use the same 1-10 scale
    as answer-level evaluations.
    """

    skill: str
    score: Score


class OverallEvaluationResponse(BaseModel):
    """
    Overall evaluation for a candidate's interview.

    This response is calculated from the stored answer evaluations.

    All candidate-level scores use a 1-10 scale.
    """

    interview_id: int
    candidate_id: int
    overall_score: Score
    skill_scores: list[SkillScore]
    strengths: list[str]
    weaknesses: list[str]


class CandidateEvaluationCreate(BaseModel):
    """
    Input for storing the overall evaluation of a candidate's interview.

    All candidate-level scores use a 1-10 scale.
    """

    model_config = ConfigDict(extra="forbid")

    interview_id: int = Field(gt=0)

    overall_score: Score

    skill_scores: dict[str, Score] = Field(
        default_factory=dict
    )

    strengths: list[NonEmptyString] = Field(
        default_factory=list
    )

    weaknesses: list[NonEmptyString] = Field(
        default_factory=list
    )


class CandidateEvaluationResponse(BaseModel):
    """
    Stored overall evaluation for a candidate's interview.

    All candidate-level scores use a 1-10 scale.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    overall_score: Score
    skill_scores: dict[str, Score] = Field(
        default_factory=dict
    )
    strengths: list[str]
    weaknesses: list[str]

