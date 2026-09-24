import logging

from app.dependencies.interfaces.llm_client_interface import (
    StructuredLLMClientInterface,
)
from app.schemas.candidate_report import GeneratedReportContent


logger = logging.getLogger(__name__)


class CandidateReportError(Exception):
    """Base error for candidate report generation failures."""


class CandidateReportService:
    """Generate structured candidate report content using the shared LLM client."""

    def __init__(
        self,
        llm_client: StructuredLLMClientInterface,
    ) -> None:
        self._llm_client = llm_client

    async def generate_report(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> GeneratedReportContent:
        try:
            return await self._llm_client.complete_structured(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=GeneratedReportContent,
            )
        except Exception as exc:
            logger.exception("Candidate report generation failed.")
            raise CandidateReportError(
                "Candidate report generation failed."
            ) from exc
