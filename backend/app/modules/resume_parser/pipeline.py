from typing import List, Union

from pydantic import BaseModel, Field

from app.core.logging import ILogger
from app.services.resume_document_intelligence import (
    DocumentIntelligenceService,
)
from app.services.resume_llm_extractor import (
    LLMExtractorService,
)
from app.services.resume_embedding_service import (
    EmbeddingService,
)
from app.schemas.resume import ResumeSchema


class ParsedCandidateResult(BaseModel):
    """
    Final result from CV Parser Pipeline.
    """

    resume_data: ResumeSchema

    semantic_sections: dict[str, str] = Field(
        default_factory=dict,
        description="Semantic resume sections prepared for embedding",
    )

    embedding_vectors: dict[str, List[float]] = Field(
        default_factory=dict,
        description="Embedding vectors generated for each semantic section",
    )

    hard_requirements: dict[str, object] = Field(
        default_factory=dict,
        description="Structured resume fields used for filtering",
    )


class CVParserPipeline:

    def __init__(
        self,
        document_service: DocumentIntelligenceService,
        llm_service: LLMExtractorService,
        embedding_service: EmbeddingService,
        logger: ILogger,
    ):
        self.document_service = document_service
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        self.logger = logger

    def parse(
        self,
        file_source: Union[str, bytes],
    ) -> ParsedCandidateResult:

        # 1. Extract text using Azure Document Intelligence
        self.logger.info(
            "Step 1: Extracting CV text..."
        )

        raw_text = self.document_service.extract_text(
            file_source
        )

        # 2. Extract structured resume JSON using Azure OpenAI
        self.logger.info(
            "Step 2: Extracting Resume Schema..."
        )

        resume = self.llm_service.extract_resume(
            raw_text
        )

        # 3. Build semantic sections
        self.logger.info(
            "Step 3: Building semantic resume sections..."
        )

        semantic_sections = (
            self.embedding_service.build_semantic_sections(
                resume
            )
        )

        # 4. Generate embeddings
        self.logger.info(
            "Step 4: Generating section embeddings..."
        )

        embedding_vectors = (
            self.embedding_service.generate_resume_embeddings(
                resume
            )
        )

        # 5. Build structured requirements
        self.logger.info(
            "Step 5: Building structured resume requirements..."
        )

        hard_requirements = (
            self.embedding_service.build_hard_requirements(
                resume
            )
        )

        return ParsedCandidateResult(
            resume_data=resume,
            semantic_sections=semantic_sections,
            embedding_vectors=embedding_vectors,
            hard_requirements=hard_requirements,
        )
