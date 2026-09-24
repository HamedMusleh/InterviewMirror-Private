"""Interface for the answer-analysis service."""

from typing import Protocol, runtime_checkable

from app.schemas.answer_analysis import AnswerAnalysis


@runtime_checkable
class IAnswerAnalysisService(Protocol):
    """Contract for services that analyze a candidate's interview answer."""

    async def analyze_answer(self, prompt: str) -> AnswerAnalysis:
        ...
