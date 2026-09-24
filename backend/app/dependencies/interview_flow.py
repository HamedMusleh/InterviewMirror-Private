from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies.adaptive_follow_up import (
    get_adaptive_follow_up_service,
)
from app.dependencies.answer_analysis import (
    get_answer_analysis_service,
)
from app.dependencies.candidate_report import (
    get_candidate_report_service,
)
from app.dependencies.candidate_report_storage import (
    get_candidate_report_handler,
)
from app.dependencies.db import get_db
from app.dependencies.evaluation import (
    get_evaluation_scoring_service,
    get_evaluation_service,
)
from app.dependencies.interfaces.adaptive_follow_up_interface import (
    IAdaptiveFollowUpService,
)
from app.dependencies.interfaces.answer_analysis_service_interface import (
    IAnswerAnalysisService,
)
from app.dependencies.interfaces.candidate_report_service_interface import (
    ICandidateReportService,
)
from app.dependencies.interview_context import (
    get_interview_answer_repository,
    get_interview_context_service,
    get_interview_question_repository,
    get_interview_repository,
)
from app.dependencies.speech_to_text import (
    get_speech_to_text_service,
)
from app.handlers.candidate_report_handler import CandidateReportHandler
from app.repositories.application_repository import (
    ApplicationRepository,
)
from app.repositories.candidate_evaluation_repository import (
    CandidateEvaluationRepository,
)
from app.repositories.candidate_report_repository import (
    CandidateReportRepository,
)
from app.repositories.candidate_repository import (
    CandidateRepository,
)
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.repositories.interview_repository import (
    InterviewRepository,
)
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.answer_analysis_service import (
    AnswerAnalysisService,
)
from app.services.adaptive_follow_up_service import (
    AdaptiveFollowUpService,
)
from app.services.evaluation_scoring_service import (
    EvaluationScoringService,
)
from app.services.evaluation_service import (
    EvaluationService,
)
from app.services.interview_context_service import (
    InterviewContextService,
)
from app.services.interview_flow_service import (
    InterviewFlowService,
)
from app.services.interview_question_service import (
    InterviewQuestionService,
)
from app.services.llm_client import (
    AzureOpenAIClient,
    get_openai_client,
)


def get_interview_question_service(
    db: Annotated[Session, Depends(get_db)],
) -> InterviewQuestionService:
    return InterviewQuestionService(db)


def get_interview_flow_service(
    interview_context_service: Annotated[
        InterviewContextService,
        Depends(get_interview_context_service),
    ],
    answer_analysis_service: Annotated[
        IAnswerAnalysisService,
        Depends(get_answer_analysis_service),
    ],
    adaptive_follow_up_service: Annotated[
        IAdaptiveFollowUpService,
        Depends(get_adaptive_follow_up_service),
    ],
    interview_question_service: Annotated[
        InterviewQuestionService,
        Depends(get_interview_question_service),
    ],
    question_repository: Annotated[
        InterviewQuestionRepository,
        Depends(get_interview_question_repository),
    ],
    answer_repository: Annotated[
        InterviewAnswerRepository,
        Depends(get_interview_answer_repository),
    ],
    interview_repository: Annotated[
        InterviewRepository,
        Depends(get_interview_repository),
    ],
    evaluation_service: Annotated[
        EvaluationService,
        Depends(get_evaluation_service),
    ],
    evaluation_scoring_service: Annotated[
        EvaluationScoringService,
        Depends(get_evaluation_scoring_service),
    ],
    candidate_report_service: Annotated[
        ICandidateReportService,
        Depends(get_candidate_report_service),
    ],
    candidate_report_handler: Annotated[
        CandidateReportHandler,
        Depends(get_candidate_report_handler),
    ],
    db: Annotated[
        Session,
        Depends(get_db),
    ],
) -> InterviewFlowService:
    return InterviewFlowService(
        interview_context_service=interview_context_service,
        answer_analysis_service=answer_analysis_service,
        adaptive_follow_up_service=adaptive_follow_up_service,
        interview_question_service=interview_question_service,
        question_repository=question_repository,
        answer_repository=answer_repository,
        interview_repository=interview_repository,
        evaluation_service=evaluation_service,
        evaluation_scoring_service=evaluation_scoring_service,
        candidate_evaluation_repository=CandidateEvaluationRepository(
            db
        ),
        candidate_report_service=candidate_report_service,
        candidate_report_handler=candidate_report_handler,
    )


def build_interview_flow_service(
    db: Session,
) -> InterviewFlowService:
    """
    Build the interview flow service outside FastAPI dependency injection.

    This is used by the WebSocket answer channel.

    A fresh database session is supplied for each submitted answer, so
    the session is not held for the lifetime of the WebSocket connection.
    """
    question_repository = InterviewQuestionRepository(db)
    answer_repository = InterviewAnswerRepository(db)
    interview_repository = InterviewRepository(db)

    interview_context_service = InterviewContextService(
        question_repository=question_repository,
        answer_repository=answer_repository,
        interview_repository=interview_repository,
        application_repository=ApplicationRepository(db),
        job_opportunity_repository=JobOpportunityRepository(db),
        speech_to_text_service=get_speech_to_text_service(),
    )

    openai_client = get_openai_client()

    evaluation_llm_client = AzureOpenAIClient(
        client=openai_client,
    )

    evaluation_service = EvaluationService(
        llm_client=evaluation_llm_client,
    )

    evaluation_scoring_service = EvaluationScoringService()

    candidate_report_repository = CandidateReportRepository(db)
    candidate_evaluation_repository = CandidateEvaluationRepository(db)
    application_repository = ApplicationRepository(db)
    candidate_repository = CandidateRepository(db)
    user_repository = UserRepository(db)
    job_opportunity_repository = JobOpportunityRepository(db)

    candidate_report_handler = CandidateReportHandler(
        candidate_report_repository=candidate_report_repository,
        candidate_evaluation_repository=candidate_evaluation_repository,
        interview_repository=interview_repository,
        application_repository=application_repository,
        candidate_repository=candidate_repository,
        user_repository=user_repository,
        job_opportunity_repository=job_opportunity_repository,
    )

    return InterviewFlowService(
        interview_context_service=interview_context_service,
        answer_analysis_service=AnswerAnalysisService(
            llm_client=openai_client,
        ),
        adaptive_follow_up_service=AdaptiveFollowUpService(
            openai_client,
        ),
        interview_question_service=InterviewQuestionService(
            db
        ),
        question_repository=question_repository,
        answer_repository=answer_repository,
        interview_repository=interview_repository,
        evaluation_service=evaluation_service,
        evaluation_scoring_service=evaluation_scoring_service,
        candidate_evaluation_repository=candidate_evaluation_repository,
        candidate_report_service=get_candidate_report_service(),
        candidate_report_handler=candidate_report_handler,
    )