from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.resume_validation import (
    ALLOWED_RESUME_CONTENT_TYPES,
    MAX_RESUME_FILE_SIZE_BYTES,
)
from app.dependencies.db import get_db
from app.dependencies.interfaces.question_generation_service_interface import (
    IQuestionGenerationService,
)
from app.dependencies.interview import get_interview_creation_service
from app.dependencies.question_generation import get_question_generation_service
from app.dependencies.resume_matching import ResumeMatchingDependencies
from app.dependencies.screening import get_screening_pipeline
from app.modules.interviews.preparation import ensure_interview_questions
from app.modules.resume_matching.pipeline import ResumeMatchingPipeline
from app.modules.resume_parser.pipeline import CVParserPipeline
from app.modules.screening.pipeline import ScreeningPipeline
from app.repositories.resume_repository import SQLAlchemyResumeRepository
from app.schemas.interview import (
    InterviewCreationResponse,
    InterviewResponse,
)
from app.schemas.screening_score import ScreeningScoreRequest
from app.services.interview_creation_service import InterviewCreationService
from app.services.resume_document_intelligence import (
    DocumentIntelligenceService,
)
from app.services.resume_embedding_service import EmbeddingService
from app.services.resume_llm_extractor import LLMExtractorService

router = APIRouter(
    prefix="/api/cv-parser",
    tags=["CV Parser"],
)


def get_cv_parser_pipeline() -> CVParserPipeline:
    document_service = DocumentIntelligenceService()
    llm_service = LLMExtractorService()
    embedding_service = EmbeddingService()
    logger = get_logger()

    return CVParserPipeline(
        document_service=document_service,
        llm_service=llm_service,
        embedding_service=embedding_service,
        logger=logger,
    )


@router.post("/parse")
async def parse_candidate_cv(
    application_id: int = Form(...),
    file: UploadFile = File(...),
    pipeline: CVParserPipeline = Depends(
        get_cv_parser_pipeline
    ),
    matching_pipeline: ResumeMatchingPipeline = Depends(
        ResumeMatchingDependencies.get_database_resume_matching_pipeline
    ),
    screening_pipeline: ScreeningPipeline = Depends(
        get_screening_pipeline
    ),
    interview_creation_service: InterviewCreationService = Depends(
        get_interview_creation_service
    ),
    question_generation_service: IQuestionGenerationService = Depends(
        get_question_generation_service
    ),
    db: Session = Depends(get_db),
):
    try:
        if file.content_type not in ALLOWED_RESUME_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Only PDF and DOCX files are supported.",
            )

        contents = await file.read()

        if len(contents) > MAX_RESUME_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=400,
                detail="File size must not exceed 10 MB.",
            )

        # Parse CV.
        result = pipeline.parse(contents)

        # Save parsed resume and original uploaded file.
        repository = SQLAlchemyResumeRepository(db)

        saved_resume = repository.save(
            application_id=application_id,
            file_name=file.filename or "resume",
            file_url="",
            file_type=file.content_type,
            file_data=contents,
            file_size=len(contents),
            resume_data=result.resume_data,
        )

        # Run resume matching.
        matching_result = await matching_pipeline.match_application(
            application_id
        )

        # Run candidate screening using the matching result.
        screening_request = ScreeningScoreRequest(
            candidate_id=matching_result.candidate_id,
            job_id=matching_result.job_id,
            application_id=matching_result.application_id,
            criteria_id=matching_result.criteria_id,
            category_scores=matching_result.category_scores,
            category_weights=matching_result.category_weights,
            matching_details=matching_result.matching_results.model_dump(),
            passing_score=matching_result.passing_score,
        )

        screening_result = screening_pipeline.score_candidate(
            screening_request
        )

        interview = None
        creation_result = None

        # Create an interview only for candidates who passed screening.
        if screening_result.final_status == "recommended":
            creation_result = (
                interview_creation_service.create_for_application(
                    application_id=saved_resume.application_id,
                )
            )

        # Finalize resume/application work and any interview that was created.
        db.commit()
        db.refresh(saved_resume)

        if creation_result is not None:
            created_interview = InterviewResponse.model_validate(
                creation_result.interview
            )

            # Generate interview questions after the interview has been saved.
            questions_generated = await ensure_interview_questions(
                interview_id=created_interview.id,
                db=db,
                generation_service=question_generation_service,
            )

            interview = InterviewCreationResponse(
                interview=created_interview,
                created=creation_result.created,
                questions_generated=questions_generated,
            )

        return {
            "resume_id": saved_resume.id,
            "application_id": saved_resume.application_id,
            "candidate_id": result.resume_data.candidate_id,
            "resume_data": result.resume_data,
            "semantic_sections": result.semantic_sections,
            "embedding_vectors": result.embedding_vectors,
            "hard_requirements": result.hard_requirements,
            "screening_result": screening_result,
            "interview": interview,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        print(f"CV Parser Error: {e}")

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/{resume_id}")
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
):
    repository = SQLAlchemyResumeRepository(db)

    resume = repository.get_by_id(resume_id)

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found.",
        )

    return {
        "id": resume.id,
        "application_id": resume.application_id,
        "file_name": resume.file_name,
        "file_url": resume.file_url,
        "file_type": resume.file_type,
        "personal_information": resume.personal_information,
        "professional_summary": resume.professional_summary,
        "skills": resume.skills,
        "experience": resume.experience,
        "education": resume.education,
        "projects": resume.projects,
        "certifications": resume.certifications,
        "languages": resume.languages,
    }


@router.get("/{resume_id}/skills")
def get_resume_skills(
    resume_id: int,
    db: Session = Depends(get_db),
):
    repository = SQLAlchemyResumeRepository(db)

    resume = repository.get_by_id(resume_id)

    if resume is None:
        raise HTTPException(
            status_code=404,
            detail="Resume not found.",
        )

    return {
        "resume_id": resume.id,
        "application_id": resume.application_id,
        "skills": resume.skills,
    }