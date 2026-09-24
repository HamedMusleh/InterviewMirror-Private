from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class TextToSpeechRequest(BaseModel):
    text: NonEmptyString


class SpokenLineRequest(BaseModel):
    """
    A line for the interviewer to say out loud.

    `style` selects one of the neural voice's expressive styles. It is the
    difference between a line that is merely intelligible and one that sounds
    like a person choosing to say it, so the caller picks per moment: a
    greeting is warm, an acknowledgement of a nervous candidate is empathetic.
    """

    text: NonEmptyString
    style: str = "chat"

    # Spoken after `text`, with a real pause in between.
    #
    # This is how the interviewer's own words are kept audibly separate from
    # the question it then reads out. Run together as one string they land as
    # a single breathless announcement; with a beat between them the first
    # part reads as a response to what the candidate just said and the second
    # as the next question.
    then: NonEmptyString | None = None
    pause_ms: int = Field(default=500, ge=0, le=3000)


class VisemeMark(BaseModel):
    """
    One mouth shape and the moment in the audio it belongs to.

    This is the whole reason the interviewer can appear to speak rather than
    merely emit sound. Azure knows exactly which shape the mouth is in at
    every instant of the audio it just generated; without capturing that here
    the browser would be left guessing from the waveform, which is what makes
    most talking avatars look dubbed.
    """

    viseme_id: int
    offset_ms: int


class WordMark(BaseModel):
    """One spoken word, for caption highlighting and emphasis cues."""

    text: str
    offset_ms: int
    duration_ms: int


class SpokenLine(BaseModel):
    """
    Audio and the timeline needed to animate it, returned together.

    Deliberately one response rather than two endpoints: the marks are
    meaningless without the exact audio they were measured against, and
    fetching them separately would let the two drift apart on a retry.
    """

    audio_base64: str
    audio_mime_type: str = "audio/mpeg"
    duration_ms: int = Field(ge=0)
    visemes: list[VisemeMark] = []
    words: list[WordMark] = []
