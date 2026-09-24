"""
What the interviewer says between the questions.

The questions themselves are generated, stored and read out verbatim by the
rest of the pipeline. This service writes only the connective tissue around
them: the hello, the reply to the opening check-in, the bridge from one
answer into the next question, and the goodbye.

That connective tissue is small in volume and almost the whole of how the
interview feels. A system that reads seven stored questions in a row with no
acknowledgement between them is a form with a voice attached. The same seven
questions, with a sentence in between showing that the last answer was
actually heard, reads as a conversation.

Every path through here has a scripted fallback. A model outage must not be
able to strand a candidate mid-interview, so a failure costs the interview
its warmth for one line and nothing else.
"""

import logging

from app.prompts.interview_conversation_prompt import (
    INTERVIEW_CONVERSATION_SYSTEM_PROMPT,
    INTERVIEWER_NAME,
    build_conversation_user_prompt,
)
from app.repositories.application_repository import ApplicationRepository
from app.repositories.candidate_repository import CandidateRepository
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_opportunity_repository import (
    JobOpportunityRepository,
)
from app.repositories.user_repository import UserRepository
from app.schemas.interview_conversation import (
    ConversationLine,
    ConversationLineRequest,
    ConversationMoment,
    GeneratedLine,
)
from app.services.llm_client import AzureOpenAIClient
from app.services.turn_completeness_service import (
    SPOKEN_SILENCE_HINT_SECONDS,
)


logger = logging.getLogger(__name__)


# High enough that forty candidates do not hear the same greeting, low enough
# that the interviewer does not start improvising. The prompt does the work of
# keeping it on task; this only varies the phrasing.
CONVERSATION_TEMPERATURE = 0.8

# Spoken lines are short by instruction. This is a backstop against a model
# that ignores that and monologues at a waiting candidate. Sized to roughly
# the twenty-five words the prompt asks for, so a line that runs away gets
# cut rather than read out in full.
MAX_SPOKEN_CHARACTERS = 170

# The greeting is the one line with more than one job: it says hello, it
# explains how to hand an answer back, and it asks how the candidate is. That
# explanation is the only time the candidate is told how the turn-taking
# works, so truncating it mid-sentence would cost them the one instruction
# they actually need. Roughly the sixty words the greeting is allowed.
MAX_GREETING_CHARACTERS = 400

# Long answers are trimmed before they reach the model. The bridge needs the
# gist and a concrete detail, not ten minutes of transcript, and sending the
# whole thing costs latency the candidate is sitting through.
MAX_ANSWER_CHARACTERS = 1_200


class InterviewConversationService:
    def __init__(
        self,
        llm_client: AzureOpenAIClient,
        interview_repository: InterviewRepository,
        application_repository: ApplicationRepository,
        job_opportunity_repository: JobOpportunityRepository,
        candidate_repository: CandidateRepository,
        user_repository: UserRepository,
        answer_repository: InterviewAnswerRepository,
    ):
        self.llm_client = llm_client
        self.interview_repository = interview_repository
        self.application_repository = application_repository
        self.job_opportunity_repository = job_opportunity_repository
        self.candidate_repository = candidate_repository
        self.user_repository = user_repository
        self.answer_repository = answer_repository

    async def compose(
        self,
        request: ConversationLineRequest,
    ) -> ConversationLine:
        """
        Write one spoken line, or fall back to a scripted one.

        The lookups run first and are also allowed to fail: not knowing the
        candidate's name costs a less personal greeting, which is a much
        smaller loss than refusing to greet them at all.
        """

        first_name, role_title = self._describe_interview(
            request.interview_id
        )

        user_prompt = build_conversation_user_prompt(
            request=self._trimmed(request),
            candidate_first_name=first_name,
            role_title=role_title,
            questions_answered=self._questions_answered(request.interview_id),
        )

        try:
            generated: GeneratedLine = (
                await self.llm_client.complete_structured(
                    system_prompt=INTERVIEW_CONVERSATION_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    response_model=GeneratedLine,
                    temperature=CONVERSATION_TEMPERATURE,
                )
            )
        except Exception:
            # Deliberately broad. Anything at all going wrong here -- a
            # configuration error, a timeout, a refusal, a schema mismatch --
            # has the same correct response: say the scripted line and keep
            # the interview moving.
            logger.exception(
                "Could not write the %s line for interview %s; using the "
                "scripted one.",
                request.moment.value,
                request.interview_id,
            )

            return _scripted_line(request.moment, first_name)

        limit = (
            MAX_GREETING_CHARACTERS
            if request.moment is ConversationMoment.GREETING
            else MAX_SPOKEN_CHARACTERS
        )

        text = " ".join(generated.text.split())[:limit].strip()

        if not text:
            return _scripted_line(request.moment, first_name)

        return ConversationLine(
            text=text,
            style=generated.style,
            mood=generated.mood,
            expects_reply=generated.expects_reply,
        )

    def _describe_interview(
        self,
        interview_id: int,
    ) -> tuple[str | None, str | None]:
        """
        Resolve who is being interviewed and for what.

        Walks interview to application to both the candidate's user record
        and the job opportunity. Any missing link yields None rather than
        raising, because this is decoration on a line that must still be
        spoken.
        """

        try:
            interview = self.interview_repository.get_by_id(interview_id)

            if interview is None:
                return None, None

            application = self.application_repository.get_by_id(
                interview.application_id
            )

            if application is None:
                return None, None

            job_opportunity = self.job_opportunity_repository.get_by_id(
                application.job_opportunity_id
            )

            role_title = (
                job_opportunity.title if job_opportunity is not None else None
            )

            candidate = self.candidate_repository.get_by_id(
                application.candidate_id
            )

            if candidate is None:
                return None, role_title

            user = self.user_repository.get_by_id(candidate.user_id)

            first_name = (
                user.first_name.strip()
                if user is not None and user.first_name
                else None
            )

            return first_name or None, role_title
        except Exception:
            logger.exception(
                "Could not describe interview %s for its spoken line.",
                interview_id,
            )

            return None, None

    def _questions_answered(self, interview_id: int) -> int:
        try:
            return len(
                self.answer_repository.get_by_interview_id(interview_id)
            )
        except Exception:
            logger.exception(
                "Could not count answers for interview %s.",
                interview_id,
            )

            return 0

    def _trimmed(
        self,
        request: ConversationLineRequest,
    ) -> ConversationLineRequest:
        """Cap the free text before it is put in front of the model."""

        return request.model_copy(
            update={
                "candidate_reply": _cap(request.candidate_reply),
                "last_answer": _cap(request.last_answer),
            }
        )


def _cap(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = " ".join(value.split())

    return cleaned[:MAX_ANSWER_CHARACTERS]


def _scripted_line(
    moment: ConversationMoment,
    first_name: str | None,
) -> ConversationLine:
    """
    The line to say when the model could not be reached.

    Deliberately generic: it makes no claim about what the candidate said,
    because at this point nothing has read it.
    """

    greeting_name = f", {first_name}" if first_name else ""

    scripts = {
        ConversationMoment.GREETING: (
            f"Hi{greeting_name}, I'm {INTERVIEWER_NAME}, an AI "
            "interviewer, and I'll be running your interview today. When "
            "you've finished an answer, just stay quiet for about "
            f"{SPOKEN_SILENCE_HINT_SECONDS} seconds and I'll take it, or "
            "press the \"I'm done\" button. How are you doing?",
            "friendly",
            "warm",
            True,
        ),
        ConversationMoment.WARMUP_REPLY: (
            "Thanks. Let's get started.",
            "chat",
            "encouraging",
            False,
        ),
        ConversationMoment.TRANSITION: (
            "Thanks. Here's the next one.",
            "chat",
            "attentive",
            False,
        ),
        ConversationMoment.CLOSING: (
            "That's everything. Thanks for your time -- your answers have "
            "been saved and the team will be in touch.",
            "friendly",
            "warm",
            False,
        ),
    }

    text, style, mood, expects_reply = scripts[moment]

    return ConversationLine(
        text=text,
        style=style,
        mood=mood,
        expects_reply=expects_reply,
        generated=False,
    )
