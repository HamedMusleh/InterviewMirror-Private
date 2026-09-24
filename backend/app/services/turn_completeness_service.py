"""
Decide how patient the interview should be with a candidate's silence.

The naive way to end a spoken turn is a fixed silence timeout: stop when the
candidate has been quiet for N seconds. Any single N is wrong. Short, and a
candidate who pauses to think about a system-design question gets cut off
mid-answer. Long, and every completed answer is followed by dead air before
the next question.

The way out is that N should not be a constant. How long a pause *means*
something depends on what was said just before it:

    "...and then I would"          -> obviously mid-thought, wait
    "...that's how I'd approach it." -> obviously finished, move on

So this module turns the transcript-so-far into a required silence duration.
It is deliberately lexical rather than model-based: it runs on every partial
transcript, several times a second, and adds no latency or cost to the hot
path. The signals are the trailing tokens, which is where English puts the
evidence of an unfinished clause.
"""

from dataclasses import dataclass
from enum import Enum
import re


class TurnState(str, Enum):
    """How finished the candidate's utterance sounds."""

    EMPTY = "empty"
    INCOMPLETE = "incomplete"
    NEUTRAL = "neutral"
    COMPLETE = "complete"


@dataclass(frozen=True)
class CompletenessAssessment:
    """How long to wait in silence, and why."""

    state: TurnState
    silence_threshold_seconds: float
    reason: str


# Words that cannot end an English sentence. If the candidate stopped talking
# immediately after one of these, they are still assembling the thought.
DANGLING_CONJUNCTIONS = frozenset(
    """
    and but or so because since although though while whereas unless until
    however therefore moreover furthermore plus nor yet whether if then
    """.split()
)

DANGLING_PREPOSITIONS = frozenset(
    """
    of to for with in on at by from about into through after before between
    against during without within across behind beyond under over upon
    """.split()
)

DANGLING_DETERMINERS = frozenset(
    """
    a an the my our your their its this that these those some any each every
    another such no both either neither
    """.split()
)

DANGLING_AUXILIARIES = frozenset(
    """
    is are was were am be been being will would shall should can could may
    might must have has had do does did going trying wanting need needs
    """.split()
)

DANGLING_COMPARATIVES = frozenset(
    """
    more less better worse than as most least greater fewer higher lower
    """.split()
)

# Hesitation markers. These are the strongest possible signal that the
# candidate is thinking rather than finished, so they get the most patience.
HESITATION_MARKERS = frozenset(
    """
    um uh erm er hmm hm like basically actually literally maybe perhaps
    """.split()
)

HESITATION_PHRASES = (
    "you know",
    "i mean",
    "let me think",
    "let's see",
    "let me see",
    "sort of",
    "kind of",
    "i guess",
    "how do i put",
    "what i'm trying to say",
)

# Explicit hand-backs. When someone says one of these they are done, and
# making them wait feels broken.
CLOSING_PHRASES = (
    "that's it",
    "that's all",
    "thats it",
    "thats all",
    "that's everything",
    "i think that covers it",
    "that covers it",
    "that's my answer",
    "yeah that's it",
    "i'm done",
    "im done",
    "does that answer",
    "hope that helps",
)

TERMINAL_PUNCTUATION = (".", "?", "!")

_WORD_PATTERN = re.compile(r"[a-z']+")


# The wait the interviewer describes out loud in its greeting.
#
# Rounded from the neutral threshold, which is the one an ordinary answer
# actually meets -- a confident finish ends sooner and an unfinished sentence
# waits longer, but neither is the number worth saying to someone who just
# wants to know when to stop talking. Kept here so the spoken figure cannot
# drift away from the behaviour it describes.
SPOKEN_SILENCE_HINT_SECONDS = 3


class TurnCompletenessAnalyzer:
    """
    Map a partial transcript onto the silence threshold it deserves.

    Thresholds are constructor arguments so they can be tuned per question
    type — a recall question deserves less patience than one that asks the
    candidate to design something.
    """

    def __init__(
        self,
        incomplete_threshold_seconds: float = 4.3,
        neutral_threshold_seconds: float = 2.8,
        complete_threshold_seconds: float = 1.9,
        opening_threshold_seconds: float = 7.0,
        short_answer_word_count: int = 8,
        short_answer_bonus_seconds: float = 1.15,
    ) -> None:
        """
        The defaults sit midway between the two settings this has had.

        The two mistakes are not symmetrical. Waiting a second too long after
        a finished answer is a small awkwardness. Cutting in a second too
        early takes the answer away mid-thought, and the candidate cannot get
        it back — they have to start again, and they have just been told by
        the system that their pause was too long. So the thresholds sit
        nearer the patient end than feels necessary when testing with short,
        confident answers.

        But patience has a limit that testing found in the other direction.
        The first setting (0.8s once an answer sounded finished) cut people
        off constantly. Correcting it to 3.0s overshot: a candidate who has
        finished sits in silence wondering whether anything is listening,
        which reads as broken rather than as patient. These are the midpoints
        of the two, which is where the behaviour was actually wanted.

        The candidate is told about this in the greeting, and there is an
        "I'm done" button for anyone who does not want to wait at all --
        both of which make a shorter wait safer than it would be on its own.
        """

        self.incomplete_threshold_seconds = incomplete_threshold_seconds
        self.neutral_threshold_seconds = neutral_threshold_seconds
        self.complete_threshold_seconds = complete_threshold_seconds
        self.opening_threshold_seconds = opening_threshold_seconds
        self.short_answer_word_count = short_answer_word_count
        self.short_answer_bonus_seconds = short_answer_bonus_seconds

    def assess(self, transcript: str) -> CompletenessAssessment:
        """Assess the utterance so far and return the silence to require."""

        stripped = (transcript or "").strip()

        if not stripped:
            return CompletenessAssessment(
                state=TurnState.EMPTY,
                silence_threshold_seconds=self.opening_threshold_seconds,
                reason="nothing said yet",
            )

        lowered = stripped.lower()
        words = _WORD_PATTERN.findall(lowered)

        if not words:
            return CompletenessAssessment(
                state=TurnState.EMPTY,
                silence_threshold_seconds=self.opening_threshold_seconds,
                reason="no recognisable words yet",
            )

        state, reason = self._classify(stripped, lowered, words)

        threshold = {
            TurnState.INCOMPLETE: self.incomplete_threshold_seconds,
            TurnState.NEUTRAL: self.neutral_threshold_seconds,
            TurnState.COMPLETE: self.complete_threshold_seconds,
        }[state]

        # Someone a handful of words in has probably only just started, even
        # if those words happen to form a grammatical sentence.
        if (
            len(words) < self.short_answer_word_count
            and state is not TurnState.COMPLETE
        ):
            threshold += self.short_answer_bonus_seconds
            reason = f"{reason}; answer still very short"

        return CompletenessAssessment(
            state=state,
            silence_threshold_seconds=round(threshold, 2),
            reason=reason,
        )

    def _classify(
        self,
        stripped: str,
        lowered: str,
        words: list[str],
    ) -> tuple[TurnState, str]:
        last_word = words[-1]

        # Hesitation beats everything else, including punctuation: "so, um."
        # is a person thinking, not a person finishing.
        if last_word in HESITATION_MARKERS:
            return (
                TurnState.INCOMPLETE,
                f"trails off on the hesitation marker '{last_word}'",
            )

        for phrase in HESITATION_PHRASES:
            if lowered.rstrip(".,!? ").endswith(phrase):
                return (
                    TurnState.INCOMPLETE,
                    f"trails off on '{phrase}'",
                )

        # Anchored to the end, not searched for anywhere in the tail:
        # "I don't think that's it at all" is not a hand-back.
        tail = lowered.rstrip(".,!? ")

        for phrase in CLOSING_PHRASES:
            if tail.endswith(phrase):
                return (
                    TurnState.COMPLETE,
                    f"explicit hand-back: '{phrase}'",
                )

        dangling = self._dangling_reason(last_word)

        if dangling is not None:
            return TurnState.INCOMPLETE, dangling

        if stripped.endswith(TERMINAL_PUNCTUATION):
            return (
                TurnState.COMPLETE,
                "ends on terminal punctuation",
            )

        # Recognised words, nothing dangling, but no sentence-final
        # punctuation either — usually an in-flight partial result.
        return (
            TurnState.NEUTRAL,
            "grammatically plausible end, but unpunctuated",
        )

    @staticmethod
    def _dangling_reason(last_word: str) -> str | None:
        categories = (
            (DANGLING_CONJUNCTIONS, "conjunction"),
            (DANGLING_PREPOSITIONS, "preposition"),
            (DANGLING_DETERMINERS, "determiner"),
            (DANGLING_AUXILIARIES, "auxiliary verb"),
            (DANGLING_COMPARATIVES, "comparative"),
        )

        for vocabulary, label in categories:
            if last_word in vocabulary:
                return f"ends on the dangling {label} '{last_word}'"

        return None
