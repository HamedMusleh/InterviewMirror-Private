"""
LLM integration for the Answer Analysis feature.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from app.dependencies.interfaces.llm_client_interface import ILLMClient
from app.schemas.answer_analysis import AnswerAnalysis
from app.services.llm_client import AZURE_OPENAI_DEPLOYMENT_NAME

logger = logging.getLogger(__name__)


class AnswerAnalysisError(Exception):
    """Base class for technical failures in the answer-analysis LLM integration."""


class LLMProviderError(AnswerAnalysisError):
    """The LLM provider call failed."""


class EmptyLLMResponseError(AnswerAnalysisError):
    """The LLM returned no content."""


class MalformedLLMResponseError(AnswerAnalysisError):
    """The LLM's content was not valid JSON."""


class InvalidResponseSchemaError(AnswerAnalysisError):
    """The parsed JSON did not validate against AnswerAnalysis."""


class AnswerAnalysisService:
    """Send a prepared answer-analysis prompt to the LLM and validate its response."""

    def __init__(self, llm_client: ILLMClient) -> None:
        self._llm_client = llm_client

    async def analyze_answer(self, prompt: str) -> AnswerAnalysis:
        raw_response = await asyncio.to_thread(
            self._call_llm,
            prompt,
        )

        response = self._parse_response(raw_response)
        self._check_technical_content(response)

        return response

    def _call_llm(self, prompt: str) -> str:
        try:
            response = self._llm_client.chat.completions.create(
                model=AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        except Exception as exc:
            logger.exception("LLM provider call failed")
            raise LLMProviderError(
                f"LLM provider call failed: {exc}"
            ) from exc

        if not response.choices:
            raise EmptyLLMResponseError(
                "LLM response contained no choices."
            )

        content = response.choices[0].message.content

        if content is None or not content.strip():
            raise EmptyLLMResponseError(
                "LLM returned an empty response."
            )

        return content

    def _parse_response(
        self,
        raw_response: str,
    ) -> AnswerAnalysis:
        if not raw_response or not raw_response.strip():
            raise EmptyLLMResponseError("LLM returned an empty response.")

        cleaned = self._strip_code_fences(raw_response.strip())

        try:
            parsed: Any = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise MalformedLLMResponseError(
                f"LLM response was not valid JSON: {exc}"
            ) from exc

        try:
            return AnswerAnalysis.model_validate(parsed)
        except ValidationError as exc:
            raise InvalidResponseSchemaError(
                f"LLM response did not match AnswerAnalysis: {exc}"
            ) from exc

    @staticmethod
    def _check_technical_content(
        response: AnswerAnalysis,
    ) -> None:
        for field_name in ("relevant_points", "missing_areas", "evidence"):
            for item in getattr(response, field_name):
                if not item.strip():
                    raise InvalidResponseSchemaError(
                        f"Every item in '{field_name}' must be a "
                        "non-blank string."
                    )

        if response.follow_up_reason is not None and not response.follow_up_reason.strip():
            raise InvalidResponseSchemaError(
                "'follow_up_reason' must be a non-empty string or null, "
                "not blank."
            )

        if response.follow_up_needed and not response.follow_up_reason:
            raise InvalidResponseSchemaError(
                "'follow_up_reason' must be provided when "
                "'follow_up_needed' is true."
            )

        if not response.follow_up_needed and response.follow_up_reason is not None:
            raise InvalidResponseSchemaError(
                "'follow_up_reason' must be null when "
                "'follow_up_needed' is false."
            )

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Tolerate models that wrap JSON in ```json ... ``` fences."""
        if text.startswith("```"):
            lines = text.split("\n")

            if lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]

            return "\n".join(lines).strip()

        return text
