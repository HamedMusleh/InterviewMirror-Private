from typing import Annotated

from fastapi import Depends
from openai import AzureOpenAI

from app.dependencies.interfaces.adaptive_follow_up_interface import (
    IAdaptiveFollowUpService,
)
from app.services.adaptive_follow_up_service import AdaptiveFollowUpService
from app.services.llm_client import get_openai_client


def get_adaptive_follow_up_service(
    client: Annotated[AzureOpenAI, Depends(get_openai_client)],
) -> IAdaptiveFollowUpService:
    return AdaptiveFollowUpService(client)