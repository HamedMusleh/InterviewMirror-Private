from typing import Protocol, runtime_checkable

from app.schemas.candidate_report import GeneratedReportContent


@runtime_checkable
class ICandidateReportService(Protocol):
    """Contract for services that generate candidate report content."""

    async def generate_report(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> GeneratedReportContent:
        ...
