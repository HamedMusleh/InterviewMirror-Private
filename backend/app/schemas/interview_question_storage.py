from enum import Enum

from pydantic import BaseModel, ConfigDict


class QuestionCategory(str, Enum):
    SKILLS = "skills"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    PROJECTS = "projects"
    CERTIFICATIONS = "certifications"
    LANGUAGES = "languages"
    SOFT_SKILLS = "soft_skills"


class GeneratedQuestion(BaseModel):
    question: str
    category: QuestionCategory
    skill: str | None = None


class GeneratedQuestions(BaseModel):
    questions: list[GeneratedQuestion]


class InterviewQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interview_id: int
    question_text: str
    question_type: str
    skill: str | None
    sequence_number: int
    is_follow_up: bool
    parent_question_id: int | None


class InterviewQuestionsResponse(BaseModel):
    questions: list[InterviewQuestionResponse]