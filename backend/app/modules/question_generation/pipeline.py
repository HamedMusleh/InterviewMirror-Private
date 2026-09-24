"""
Orchestration for the Role-Based Question Generation feature.
"""

from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.prompts.question_generation_prompt import (
    NUMBER_OF_QUESTIONS,
    build_question_prompt,
)
from app.schemas.interview_question import QuestionGenerationResponse
from app.schemas.question_generation import QuestionGenerationInput


async def run_question_generation_pipeline(
    request: QuestionGenerationInput,
    service: IQuestionGenerationService,
) -> QuestionGenerationResponse:
    prompt = build_question_prompt(
        job_description=request.job_description,
        screening_data=request.screening_criteria,
    )

    return await service.generate_questions(
        prompt=prompt,
        number_of_questions=NUMBER_OF_QUESTIONS,
    )
