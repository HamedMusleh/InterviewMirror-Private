from app.dependencies.interfaces.llm_client_interface import (
    StructuredLLMClientInterface,
)
from app.prompts.resume_matching_prompt import SYSTEM_PROMPT, build_user_prompt
from app.schemas.resume_matching import (
    DatabaseMatchingResponse,
    MATCHING_CATEGORY_NAMES,
    MatchingRequest,
    MatchingResponse,
    MatchingResults,
)
from app.repositories.resume_matching_repository import (
    ResumeMatchingRepository,
)
from app.services.resume_matching_service import ResumeMatchingService


class ResumeMatchingPipeline:
    """Orchestrates model evaluation and matching-result normalization."""

    def __init__(
        self,
        llm_client: StructuredLLMClientInterface,
        matching_service: ResumeMatchingService,
        repository: ResumeMatchingRepository | None = None,
    ):
        self.llm_client = llm_client
        self.matching_service = matching_service
        self.repository = repository

    async def match(self, request: MatchingRequest) -> MatchingResponse:
        return await self._evaluate(request)

    async def match_application(
        self,
        application_id: int,
    ) -> DatabaseMatchingResponse:
        if self.repository is None:
            raise RuntimeError(
                "A resume matching repository is required for database matching"
            )

        stored_input = self.repository.load_for_application(application_id)
        response = await self._evaluate(stored_input.request)

        category_scores = {
            category_name: {
                "score": getattr(
                    response.matching_results,
                    category_name,
                ).score,
                "status": getattr(
                    response.matching_results,
                    category_name,
                ).status,
            }
            for category_name in MATCHING_CATEGORY_NAMES
        }

        return DatabaseMatchingResponse(
            **response.model_dump(),
            application_id=stored_input.application_id,
            job_opportunity_id=stored_input.job_opportunity_id,
            criteria_id=stored_input.criteria_id,
            category_scores=category_scores,
            category_weights=stored_input.category_weights,
            passing_score=stored_input.passing_score,
        )

    async def _evaluate(self, request: MatchingRequest) -> MatchingResponse:
        results = await self.llm_client.complete_structured(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(request),
            response_model=MatchingResults,
        )
        return self.matching_service.build_response(request, results)
