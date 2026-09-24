from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.schemas.interview_context import (
    InterviewContext,
    InterviewContextRequest,
    PriorInteraction,
)
from app.services.speech_to_text_service import SpeechToTextService


class InterviewContextService:
    def __init__(
        self,
        question_repository: InterviewQuestionRepository,
        answer_repository: InterviewAnswerRepository,
        interview_repository: InterviewRepository,
        application_repository: ApplicationRepository,
        job_opportunity_repository: JobOpportunityRepository,
        speech_to_text_service: SpeechToTextService,
    ):
        self.question_repository = question_repository
        self.answer_repository = answer_repository
        self.interview_repository = interview_repository
        self.application_repository = application_repository
        self.job_opportunity_repository = job_opportunity_repository
        self.speech_to_text_service = speech_to_text_service

    def build_context(
        self,
        request: InterviewContextRequest,
    ) -> InterviewContext:
        question = self.question_repository.get_by_id(
            request.question_id
        )

        if question is None:
            raise ValueError(
                f"Interview question {request.question_id} not found"
            )

        if question.interview_id != request.interview_id:
            raise ValueError(
                f"Question {request.question_id} does not belong to "
                f"interview {request.interview_id}"
            )

        interview = self.interview_repository.get_by_id(
            request.interview_id
        )

        if interview is None:
            raise ValueError(
                f"Interview {request.interview_id} not found"
            )

        application = self.application_repository.get_by_id(
            interview.application_id
        )

        if application is None:
            raise ValueError(
                f"Application {interview.application_id} not found"
            )

        job_opportunity = self.job_opportunity_repository.get_by_id(
            application.job_opportunity_id
        )

        if job_opportunity is None:
            raise ValueError(
                f"Job opportunity {application.job_opportunity_id} "
                "not found"
            )

        answer_text = self._resolve_answer_text(request)

        previous_interactions = self._build_previous_interactions(
            interview_id=request.interview_id,
            before_sequence_number=question.sequence_number,
        )

        return InterviewContext(
            interview_id=request.interview_id,
            question_id=request.question_id,
            role=job_opportunity.title,
            question=question.question_text,
            question_type=question.question_type,
            skill=question.skill,
            answer=answer_text,
            previous_interactions=previous_interactions,
        )

    def _resolve_answer_text(
        self,
        request: InterviewContextRequest,
    ) -> str:
        if request.answer_text:
            return request.answer_text

        media_url = request.audio_url or request.video_url

        if media_url:
            return self.speech_to_text_service.transcribe(media_url)

        raise ValueError(
            "No answer content (answer_text, audio_url, or video_url) "
            "was provided"
        )

    def _build_previous_interactions(
        self,
        interview_id: int,
        before_sequence_number: int,
    ) -> list[PriorInteraction]:
        previous_questions = [
            question
            for question in self.question_repository.get_by_interview_id(
                interview_id
            )
            if question.sequence_number < before_sequence_number
        ]

        answers_by_question_id = {
            answer.question_id: answer
            for answer in self.answer_repository.get_by_interview_id(
                interview_id
            )
        }

        previous_interactions: list[PriorInteraction] = []

        for previous_question in previous_questions:
            previous_answer = answers_by_question_id.get(
                previous_question.id
            )

            if previous_answer is None:
                continue

            previous_answer_text = (
                previous_answer.answer_text
                or previous_answer.transcript
            )

            if not previous_answer_text:
                continue

            previous_interactions.append(
                PriorInteraction(
                    question=previous_question.question_text,
                    answer=previous_answer_text,
                )
            )

        return previous_interactions
