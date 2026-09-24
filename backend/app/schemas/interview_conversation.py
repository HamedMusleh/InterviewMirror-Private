from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class ConversationMoment(str, Enum):
    """
    The four points in an interview where the interviewer speaks as itself
    rather than reading a prepared question.
    """

    GREETING = "greeting"
    WARMUP_REPLY = "warmup_reply"
    TRANSITION = "transition"
    CLOSING = "closing"


# The voice styles the interviewer is allowed to pick from, and the facial
# expressions the avatar can hold. Both are constrained rather than free text
# so the model cannot invent a style the voice will silently ignore or a mood
# the avatar has no rendering for.
LineStyle = Literal[
    "chat",
    "friendly",
    "cheerful",
    "empathetic",
    "hopeful",
]

LineMood = Literal[
    "warm",
    "attentive",
    "thoughtful",
    "encouraging",
    "neutral",
]


class ConversationLineRequest(BaseModel):
    interview_id: int
    moment: ConversationMoment

    # What the candidate said during the unscored opening check-in.
    candidate_reply: str | None = None

    # How many check-in exchanges have already happened.
    #
    # Small talk needs a bound or it becomes its own interview. Zero means
    # the interviewer may keep the conversation going for one more turn;
    # anything higher means it must wrap up and begin.
    warmup_exchanges: int = 0

    # The exchange the interviewer is moving on from.
    last_question: str | None = None
    last_answer: str | None = None

    # Where it is moving to. The question text is passed so the bridge can
    # lead into it naturally, but the interviewer never speaks it -- the room
    # reads the stored question verbatim, so a paraphrase cannot drift away
    # from the question the answer is scored against.
    next_question: str | None = None
    next_is_follow_up: bool = False


class GeneratedLine(BaseModel):
    """What the model returns. Kept minimal so it is hard to get wrong."""

    text: str = Field(
        description=(
            "What the interviewer says out loud. One short sentence; two "
            "only if the second is very short."
        )
    )
    style: LineStyle
    mood: LineMood
    expects_reply: bool = Field(
        description=(
            "True when this line ends on a question the candidate is meant "
            "to answer out loud, so the room should listen instead of "
            "moving on."
        )
    )


class ConversationLine(BaseModel):
    """
    A line the interviewer will say, plus how to say it and how to look
    while saying it.

    Style and mood travel with the text because they are decided by the same
    judgement. Whether a candidate just admitted to being nervous determines
    the words, the vocal warmth and the expression all at once, and splitting
    that across three systems is how they end up disagreeing.
    """

    text: str
    style: LineStyle = "chat"
    mood: LineMood = "warm"

    # True when the interviewer has just asked the candidate something and
    # is waiting for an answer. This is what lets small talk actually be a
    # conversation: the room reopens the microphone instead of ploughing on
    # into the first interview question.
    expects_reply: bool = False

    # True when the words came from the scripted fallback because the model
    # was unreachable. The interview carries on either way; this only exists
    # so the difference is visible in logs and responses.
    generated: bool = True
