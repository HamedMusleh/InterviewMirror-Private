"""
Orchestration for the Answer Analysis feature.
"""

from app.dependencies.interfaces.answer_analysis_service_interface import (
    IAnswerAnalysisService,
)
from app.prompts.answer_analysis_prompt import build_answer_analysis_prompt
from app.schemas.answer_analysis import AnswerAnalysis, AnswerAnalysisInput


async def run_answer_analysis_pipeline(
    request: AnswerAnalysisInput,
    service: IAnswerAnalysisService,
) -> AnswerAnalysis:
    prompt = build_answer_analysis_prompt(request)

    return await service.analyze_answer(prompt)
