from __future__ import annotations

from datetime import datetime, timezone

from app.database.models.interview_question import InterviewQuestion
from app.dependencies.interfaces.adaptive_follow_up_interface import (
    IAdaptiveFollowUpService,
)
from app.dependencies.interfaces.answer_analysis_service_interface import (
    IAnswerAnalysisService,
)
from app.dependencies.interfaces.candidate_report_service_interface import (
    ICandidateReportService,
)
from app.handlers.candidate_report_handler import CandidateReportHandler
from app.modules.candidate_report.orchestration import (
    generate_and_store_candidate_report,
)
from app.prompts.answer_analysis_prompt import build_answer_analysis_prompt
from app.repositories.candidate_evaluation_repository import (
    CandidateEvaluationRepository,
)
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.schemas.adaptive_follow_up import FollowUpQuestionRequest
from app.schemas.answer_analysis import (
    AnswerAnalysis,
    AnswerAnalysisInput,
)
from app.schemas.candidate_report import CandidateReportInput
from app.schemas.evaluation import EvaluationInput
from app.schemas.interview_context import InterviewContextRequest
from app.schemas.interview_flow import (
    InterviewFlowResult,
    InterviewStatusResponse,
)
from app.schemas.interview_question_storage import InterviewQuestionResponse
from app.services.candidate_evaluation_service import (
    CandidateEvaluationService,
)
from app.services.evaluation_scoring_service import (
    EvaluationScoringService,
)
from app.services.evaluation_service import EvaluationService
from app.services.interview_context_service import InterviewContextService
from app.services.interview_question_service import InterviewQuestionService


INTERVIEW_STATUS_COMPLETED = "completed"


class InterviewFlowService:
    def __init__(
        self,
        interview_context_service: InterviewContextService,
        answer_analysis_service: IAnswerAnalysisService,
        adaptive_follow_up_service: IAdaptiveFollowUpService,
        interview_question_service: InterviewQuestionService,
        question_repository: InterviewQuestionRepository,
        answer_repository: InterviewAnswerRepository,
        interview_repository: InterviewRepository,
        evaluation_service: EvaluationService,
        evaluation_scoring_service: EvaluationScoringService,
        candidate_evaluation_repository: CandidateEvaluationRepository,
        candidate_report_service: ICandidateReportService,
        candidate_report_handler: CandidateReportHandler,
    ):
        self.interview_context_service = interview_context_service
        self.answer_analysis_service = answer_analysis_service
        self.adaptive_follow_up_service = adaptive_follow_up_service
        self.interview_question_service = interview_question_service
        self.question_repository = question_repository
        self.answer_repository = answer_repository
        self.interview_repository = interview_repository
        self.evaluation_service = evaluation_service
        self.evaluation_scoring_service = evaluation_scoring_service
        self.candidate_evaluation_repository = (
            candidate_evaluation_repository
        )
        self.candidate_report_service = candidate_report_service
        self.candidate_report_handler = candidate_report_handler

    async def start(
        self,
        interview_id: int,
    ) -> InterviewStatusResponse:
        """
        Record that the candidate has begun, and report where they are.

        Called every time the room opens, including after a reload, and the
        stamp is written only once -- so the elapsed clock counts from the
        real beginning of the interview rather than from the last time the
        page happened to load.

        A completed interview is left alone: reopening one must not restart
        its clock, and get_status will report it as finished either way.
        """

        interview = self.interview_repository.get_by_id(interview_id)

        if interview is None:
            raise ValueError(
                f"Interview {interview_id} was not found."
            )

        if interview.status != INTERVIEW_STATUS_COMPLETED:
            self.interview_repository.mark_started(interview_id)

        return await self.get_status(interview_id)

    async def get_status(
        self,
        interview_id: int,
    ) -> InterviewStatusResponse:
        interview = self.interview_repository.get_by_id(interview_id)

        if interview is None:
            raise ValueError(
                f"Interview {interview_id} was not found."
            )

        if interview.status == INTERVIEW_STATUS_COMPLETED:
            return InterviewStatusResponse(
                interview_id=interview_id,
                status=interview.status,
                completed=True,
                next_question=None,
                answered_count=len(
                    self.answer_repository.get_answered_question_ids(
                        interview_id
                    )
                ),
                started_at=interview.started_at,
                elapsed_seconds=_elapsed_seconds(interview),
            )

        questions = self.question_repository.get_by_interview_id(
            interview_id
        )

        answered_question_ids = (
            self.answer_repository.get_answered_question_ids(
                interview_id
            )
        )

        answered_ids = set(answered_question_ids)

        ordered_questions = sorted(
            questions,
            key=lambda question: (
                question.sequence_number,
                question.id,
            ),
        )

        next_question = next(
            (
                question
                for question in ordered_questions
                if question.id not in answered_ids
            ),
            None,
        )

        if next_question is None:
            return InterviewStatusResponse(
                interview_id=interview_id,
                status=interview.status,
                completed=True,
                next_question=None,
                answered_count=len(answered_ids),
                started_at=interview.started_at,
                elapsed_seconds=_elapsed_seconds(interview),
            )

        return InterviewStatusResponse(
            interview_id=interview_id,
            status=interview.status,
            completed=False,
            next_question=InterviewQuestionResponse.model_validate(
                next_question
            ),
            answered_count=len(answered_ids),
            started_at=interview.started_at,
            elapsed_seconds=_elapsed_seconds(interview),
        )

    async def submit_answer(
        self,
        request: InterviewContextRequest,
    ) -> InterviewFlowResult:
        """
        Process one candidate answer through the complete interview flow.

        Flow:

        1. Build interview context.
        2. Store the candidate answer.
        3. Run Answer Analysis once.
        4. Use the Answer Analysis result as input to Evaluation.
        5. Calculate the deterministic final evaluation score.
        6. Store the answer-level evaluation.
        7. Generate a follow-up question when required.
        8. Otherwise move to the next question.
        9. If there are no more questions:
           - Complete the interview.
           - Persist the candidate-level evaluation.
           - Aggregate strengths and weaknesses.
           - Generate and store the candidate report.
        """
        interview = self.interview_repository.get_by_id(
            request.interview_id
        )

        if interview is None:
            raise ValueError(
                f"Interview {request.interview_id} was not found."
            )

        if interview.status == INTERVIEW_STATUS_COMPLETED:
            raise ValueError(
                f"Interview {request.interview_id} has already been completed."
            )

        context = self.interview_context_service.build_context(request)

        stored_answer = self.answer_repository.create(
            question_id=request.question_id,
            answer_text=request.answer_text,
            audio_url=request.audio_url,
            video_url=request.video_url,
            transcript=(
                context.answer
                if request.answer_text is None
                else None
            ),
        )

        current_question = self.question_repository.get_by_id(
            request.question_id
        )

        if current_question is None:
            raise ValueError(
                f"Interview question {request.question_id} was not found."
            )

        analysis_input = AnswerAnalysisInput(
            **context.model_dump()
        )

        analysis = await self._analyze_answer(
            analysis_input
        )

        await self._evaluate_and_store_answer(
            answer_id=stored_answer.id,
            analysis_input=analysis_input,
            analysis=analysis,
        )

        if not current_question.is_follow_up:
            follow_up_result = await self._try_generate_follow_up(
                request=request,
                analysis_input=analysis_input,
                analysis=analysis,
            )

            if follow_up_result is not None:
                return follow_up_result

        return await self._resolve_next_question(
            interview_id=request.interview_id,
            current_question=current_question,
        )

    async def _analyze_answer(
        self,
        analysis_input: AnswerAnalysisInput,
    ) -> AnswerAnalysis:
        prompt = build_answer_analysis_prompt(
            analysis_input
        )

        return await self.answer_analysis_service.analyze_answer(
            prompt
        )

    async def _evaluate_and_store_answer(
        self,
        answer_id: int,
        analysis_input: AnswerAnalysisInput,
        analysis: AnswerAnalysis,
    ) -> None:
        """
        Convert Answer Analysis output into Evaluation input,
        run the evaluation pipeline, and persist the resulting
        answer evaluation.
        """
        evaluation_input = EvaluationInput(
            answer_id=answer_id,
            question_id=analysis_input.question_id,
            question=analysis_input.question,
            skill=analysis_input.skill,
            answer=analysis_input.answer,
            answer_quality=analysis.answer_quality,
            relevant_points=analysis.relevant_points,
            missing_areas=analysis.missing_areas,
            evidence=analysis.evidence,
        )

        evaluation_result = (
            await self.evaluation_service.evaluate_answer(
                evaluation_input
            )
        )

        final_result = (
            self.evaluation_scoring_service.build_final_result(
                evaluation_result
            )
        )

        criteria_scores = final_result.criteria_scores

        self.candidate_evaluation_repository.create_answer_evaluation(
            answer_id=answer_id,
            relevance_score=round(
                criteria_scores.relevance
            ),
            correctness_score=round(
                criteria_scores.correctness
            ),
            depth_score=round(
                criteria_scores.depth
            ),
            practicality_score=round(
                criteria_scores.practicality
            ),
            score=final_result.score,
            strengths=final_result.strengths,
            weaknesses=final_result.weaknesses,
        )

    async def _try_generate_follow_up(
        self,
        request: InterviewContextRequest,
        analysis_input: AnswerAnalysisInput,
        analysis: AnswerAnalysis,
    ) -> InterviewFlowResult | None:
        if not analysis.follow_up_needed:
            return None

        follow_up_request = FollowUpQuestionRequest(
            question_id=analysis_input.question_id,
            question=analysis_input.question,
            answer=analysis_input.answer,
            question_type=analysis_input.question_type,
            skill=analysis_input.skill,
            missing_areas=analysis.missing_areas,
            follow_up_needed=analysis.follow_up_needed,
            follow_up_reason=analysis.follow_up_reason,
        )

        follow_up = (
            self.adaptive_follow_up_service.generate_follow_up_question(
                follow_up_request
            )
        )

        if follow_up is None:
            return None

        stored_question = (
            self.interview_question_service.store_follow_up_question(
                interview_id=request.interview_id,
                follow_up=follow_up,
            )
        )

        return InterviewFlowResult(
            follow_up_generated=True,
            next_question=InterviewQuestionResponse.model_validate(
                stored_question
            ),
            interview_completed=False,
        )

    async def _resolve_next_question(
        self,
        interview_id: int,
        current_question: InterviewQuestion,
    ) -> InterviewFlowResult:
        if current_question.is_follow_up:
            parent_question = self.question_repository.get_by_id(
                current_question.parent_question_id
            )

            if parent_question is None:
                raise ValueError(
                    "Parent question was not found for follow-up question "
                    f"{current_question.id}."
                )

            root_sequence_number = (
                parent_question.sequence_number
            )
        else:
            root_sequence_number = (
                current_question.sequence_number
            )

        upcoming_questions = [
            question
            for question in self.question_repository.get_by_interview_id(
                interview_id
            )
            if not question.is_follow_up
            and question.sequence_number > root_sequence_number
        ]

        if upcoming_questions:
            next_question = min(
                upcoming_questions,
                key=lambda question: question.sequence_number,
            )

            return InterviewFlowResult(
                follow_up_generated=False,
                next_question=InterviewQuestionResponse.model_validate(
                    next_question
                ),
                interview_completed=False,
            )

        self.interview_repository.update_status(
            interview_id,
            INTERVIEW_STATUS_COMPLETED,
        )

        # Freezes the elapsed clock: once ended_at is set, the reported
        # duration is the length of the interview rather than the time since
        # it started, so reopening a finished interview does not show a
        # timer that is still climbing.
        self.interview_repository.mark_ended(interview_id)

        await self._create_candidate_report(
            interview_id=interview_id,
        )

        return InterviewFlowResult(
            follow_up_generated=False,
            next_question=None,
            interview_completed=True,
        )

    async def _create_candidate_report(
        self,
        interview_id: int,
    ) -> None:
        """
        Generate and store the candidate report after the interview
        has been completed.

        Candidate-level score data is loaded from candidate_evaluations,
        while strengths and weaknesses are aggregated from the
        answer-level evaluations.
        """
        candidate_evaluation_service = CandidateEvaluationService(
            self.candidate_evaluation_repository.db
        )

        evaluation = (
            self.candidate_evaluation_repository.get_by_interview_id(
                interview_id
            )
        )

        if evaluation is None:
            evaluation = (
                candidate_evaluation_service
                .calculate_and_store_candidate_evaluation(
                    interview_id=interview_id,
                )
            )

        if evaluation is None:
            raise ValueError(
                "Candidate evaluation could not be created for "
                f"interview {interview_id}."
            )

        evaluation_results = (
            self.candidate_evaluation_repository.get_interview_evaluations(
                interview_id=interview_id,
            )
        )

        strengths: list[str] = []
        weaknesses: list[str] = []

        for answer_evaluation, _ in evaluation_results:
            strengths.extend(
                answer_evaluation.strengths or []
            )
            weaknesses.extend(
                answer_evaluation.weaknesses or []
            )

        strengths = candidate_evaluation_service._unique_strings(
            strengths
        )

        weaknesses = candidate_evaluation_service._unique_strings(
            weaknesses
        )

        report_input = CandidateReportInput(
            id=evaluation.id,
            interview_id=evaluation.interview_id,
            overall_score=evaluation.overall_score,
            skill_scores=evaluation.skill_scores,
            strengths=strengths,
            weaknesses=weaknesses,
        )

        await generate_and_store_candidate_report(
            evaluation=report_input,
            report_service=self.candidate_report_service,
            report_handler=self.candidate_report_handler,
        )


def _elapsed_seconds(interview) -> int:
    """
    How long the interview has been running, in whole seconds.

    Measured here rather than in the browser so a candidate whose device
    clock is wrong still sees the right number. Stops at ended_at once the
    interview is over, and never goes negative -- a stored timestamp very
    slightly in the future (clock adjustment on the database host, say)
    should read as zero rather than as a negative duration.
    """

    started_at = getattr(interview, "started_at", None)

    if started_at is None:
        return 0

    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)

    ended_at = getattr(interview, "ended_at", None)

    if ended_at is None:
        ended_at = datetime.now(timezone.utc)
    elif ended_at.tzinfo is None:
        ended_at = ended_at.replace(tzinfo=timezone.utc)

    return max(0, int((ended_at - started_at).total_seconds()))
