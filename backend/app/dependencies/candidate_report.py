"""Dependency provider for candidate report generation."""

from functools import lru_cache

from app.dependencies.interfaces.candidate_report_service_interface import (
    ICandidateReportService,
)
from app.services.candidate_report_service import CandidateReportService
from app.services.llm_client import AzureOpenAIClient


@lru_cache
def get_candidate_report_service() -> ICandidateReportService:
    """Build the candidate report service using the shared structured LLM client."""
    return CandidateReportService(
        llm_client=AzureOpenAIClient()
    )
