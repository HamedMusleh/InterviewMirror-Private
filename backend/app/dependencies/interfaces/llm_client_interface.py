from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel


ModelT = TypeVar("ModelT", bound=BaseModel)


@runtime_checkable
class ILLMClient(Protocol):
    """
    Structural contract for the LLM client used by services (currently
    `app.services.llm_client.get_openai_client`, backed by the Azure
    OpenAI SDK's `AzureOpenAI` client).

    This is documentation of the shape services rely on
    (`client.chat.completions.create(...)`) so a future provider swap
    is easier to reason about. `AzureOpenAI` already satisfies this
    protocol structurally, so `get_openai_client()` keeps returning
    the concrete `AzureOpenAI` type - existing behavior and type hints
    are unchanged.
    """

    chat: object


class StructuredLLMClientInterface(Protocol):
    """Contract for clients that return validated structured responses."""

    async def complete_structured(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: type[ModelT],
    ) -> ModelT:
        """Return a validated structured response from the configured model."""
