import asyncio
import inspect
from functools import lru_cache
from typing import Any

from openai import AzureOpenAI

from app.core.config import settings


AZURE_OPENAI_DEPLOYMENT_NAME = settings.azure_openai_deployment_name


@lru_cache
def get_openai_client() -> AzureOpenAI:
    """
    Returns a cached AzureOpenAI client instance.

    The client is created when the dependency is first resolved
    instead of during module import.
    """
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_key,
        api_version=settings.azure_openai_api_version,
    )


class LLMClientError(Exception):
    """Base error for structured LLM calls."""


class LLMConfigurationError(LLMClientError):
    """Raised when Azure OpenAI configuration is missing."""


class LLMRequestError(LLMClientError):
    """Raised when an Azure OpenAI request fails."""


class LLMResponseError(LLMClientError):
    """Raised when Azure OpenAI returns no usable structured response."""


class AzureOpenAIClient:
    """Adapt the shared Azure client for asynchronous structured responses."""

    def __init__(
        self,
        client: Any | None = None,
        deployment_name: str | None = None,
    ) -> None:
        self._client = client
        self._deployment_name = deployment_name

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                self._client = get_openai_client()
            except Exception as exc:
                raise LLMConfigurationError(
                    "Unable to initialize the Azure OpenAI client"
                ) from exc
        return self._client

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type,
        temperature: float = 0,
    ):
        """
        `temperature` defaults to 0 because every existing caller extracts or
        classifies, where a stable answer is the point. Conversational
        callers pass it up: an interviewer that greets forty candidates with
        the same sentence stops sounding like a person.
        """

        client = self._get_client()
        deployment_name = self._deployment_name or AZURE_OPENAI_DEPLOYMENT_NAME

        if not deployment_name:
            raise LLMConfigurationError(
                "Azure OpenAI deployment name is not configured"
            )

        try:
            response = await asyncio.to_thread(
                client.beta.chat.completions.parse,
                model=deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=response_model,
                temperature=temperature,
            )
            if inspect.isawaitable(response):
                response = await response
        except LLMClientError:
            raise
        except Exception as exc:
            raise LLMRequestError(
                "Azure OpenAI matching request failed"
            ) from exc

        if not response.choices:
            raise LLMResponseError("Azure OpenAI returned no choices")

        message = response.choices[0].message
        parsed = getattr(message, "parsed", None)
        if parsed is None:
            refusal = getattr(message, "refusal", None)
            detail = "Azure OpenAI returned no structured matching result"
            if refusal:
                detail += ": " + str(refusal)
            raise LLMResponseError(detail)

        if isinstance(parsed, response_model):
            return parsed

        try:
            return response_model.model_validate(parsed)
        except Exception as exc:
            raise LLMResponseError(
                "Azure OpenAI response did not match the expected schema"
            ) from exc
