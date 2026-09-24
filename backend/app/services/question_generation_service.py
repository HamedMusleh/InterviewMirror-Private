"""
LLM integration for the Role-Based Question Generation feature.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from app.dependencies.interfaces.llm_client_interface import ILLMClient
from app.schemas.interview_question import QuestionGenerationResponse
from app.services.llm_client import AZURE_OPENAI_DEPLOYMENT_NAME

logger = logging.getLogger(__name__)


class QuestionGenerationError(Exception):
    """Base class for technical failures in the question-generation LLM integration."""


class LLMProviderError(QuestionGenerationError):
    """The LLM provider call failed."""


class EmptyLLMResponseError(QuestionGenerationError):
    """The LLM returned no content."""


class MalformedLLMResponseError(QuestionGenerationError):
    """The LLM's content was not valid JSON."""


class InvalidResponseSchemaError(QuestionGenerationError):
    """The parsed JSON did not validate against QuestionGenerationResponse."""


class QuestionCountMismatchError(QuestionGenerationError):
    """The LLM returned a different number of questions than requested."""


class QuestionGenerationService:
    """Send a built question-generation prompt to the LLM and validate its response."""

    def __init__(self, llm_client: ILLMClient) -> None:
        self._llm_client = llm_client

    async def generate_questions(
        self,
        prompt: str,
        number_of_questions: int,
    ) -> QuestionGenerationResponse:
        raw_response = await asyncio.to_thread(
            self._call_llm,
            prompt,
        )

        response = self._parse_response(raw_response)
        self._check_technical_content(response)
        self._check_question_count(response, number_of_questions)

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
    ) -> QuestionGenerationResponse:
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
            return QuestionGenerationResponse.model_validate(parsed)
        except ValidationError as exc:
            raise InvalidResponseSchemaError(
                f"LLM response did not match QuestionGenerationResponse: {exc}"
            ) from exc

    @staticmethod
    def _check_technical_content(
        response: QuestionGenerationResponse,
    ) -> None:
        if not response.questions:
            raise InvalidResponseSchemaError(
                "'questions' must not be empty."
            )

        for item in response.questions:
            if not item.question.strip():
                raise InvalidResponseSchemaError(
                    "Every question must be a non-blank string."
                )

            if item.skill is not None and not item.skill.strip():
                raise InvalidResponseSchemaError(
                    "'skill' must be a non-empty string or null, not blank."
                )

    @staticmethod
    def _check_question_count(
        response: QuestionGenerationResponse,
        requested: int,
    ) -> None:
        actual = len(response.questions)

        if actual != requested:
            raise QuestionCountMismatchError(
                f"Requested {requested} questions but the LLM returned {actual}."
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