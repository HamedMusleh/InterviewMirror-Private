"""
Tests for TurnCompletenessAnalyzer.

This is the piece that decides how patient the interview should be with a
pause, so the behaviour worth pinning down is comparative: an obviously
unfinished sentence must always earn more silence than an obviously finished
one. The exact seconds are tuning; the ordering is the contract.
"""

import pytest

from app.services.turn_completeness_service import (
    TurnCompletenessAnalyzer,
    TurnState,
)


@pytest.fixture
def analyzer():
    return TurnCompletenessAnalyzer()


# A long enough answer that the short-answer bonus does not apply, so these
# cases isolate the effect of the trailing token alone.
PREAMBLE = (
    "So the way I would approach this problem in a production system is "
)


def assess(analyzer, tail):
    return analyzer.assess(PREAMBLE + tail)


# --------------------------------------------------------------- unfinished


@pytest.mark.parametrize(
    "tail",
    [
        "to use a load balancer and",
        "caching, but",
        "fine because",
        "worth doing so",
        "an approach that works if",
    ],
)
def test_dangling_conjunctions_are_incomplete(analyzer, tail):
    assert assess(analyzer, tail).state is TurnState.INCOMPLETE


@pytest.mark.parametrize(
    "tail",
    [
        "a trade-off between",
        "something I learned from",
        "mostly about",
        "a queue in front of",
    ],
)
def test_dangling_prepositions_are_incomplete(analyzer, tail):
    assert assess(analyzer, tail).state is TurnState.INCOMPLETE


@pytest.mark.parametrize(
    "tail",
    ["to introduce a", "it depends on the", "we looked at another"],
)
def test_dangling_determiners_are_incomplete(analyzer, tail):
    assert assess(analyzer, tail).state is TurnState.INCOMPLETE


@pytest.mark.parametrize(
    "tail",
    ["something the team would", "a decision that could", "the index is"],
)
def test_dangling_auxiliaries_are_incomplete(analyzer, tail):
    assert assess(analyzer, tail).state is TurnState.INCOMPLETE


def test_dangling_comparative_is_incomplete(analyzer):
    assert assess(analyzer, "making the query more").state is (
        TurnState.INCOMPLETE
    )


@pytest.mark.parametrize("marker", ["um", "uh", "hmm", "like", "basically"])
def test_hesitation_markers_are_incomplete(analyzer, marker):
    assert assess(analyzer, f"a caching layer, {marker}").state is (
        TurnState.INCOMPLETE
    )


@pytest.mark.parametrize(
    "phrase", ["you know", "I mean", "let me think", "sort of"]
)
def test_hesitation_phrases_are_incomplete(analyzer, phrase):
    assert assess(analyzer, f"a caching layer, {phrase}").state is (
        TurnState.INCOMPLETE
    )


def test_hesitation_beats_terminal_punctuation(analyzer):
    """'so, um.' is someone thinking, not someone finishing."""

    assert assess(analyzer, "a caching layer, um.").state is (
        TurnState.INCOMPLETE
    )


# ----------------------------------------------------------------- finished


def test_terminal_punctuation_is_complete(analyzer):
    assert assess(analyzer, "to put a cache in front of the database.").state is (
        TurnState.COMPLETE
    )


@pytest.mark.parametrize("mark", [".", "?", "!"])
def test_every_terminal_mark_counts(analyzer, mark):
    assert assess(analyzer, f"to add a cache{mark}").state is (
        TurnState.COMPLETE
    )


@pytest.mark.parametrize(
    "phrase",
    ["that's it", "that's all", "I'm done", "I think that covers it"],
)
def test_explicit_hand_backs_are_complete(analyzer, phrase):
    assert assess(analyzer, f"to add a cache, and {phrase}").state is (
        TurnState.COMPLETE
    )


@pytest.mark.parametrize(
    "tail",
    [
        "not sure that's it at all",
        "that's all the caching we needed to add",
    ],
)
def test_closing_phrases_only_count_at_the_very_end(analyzer, tail):
    """A hand-back phrase buried mid-sentence is not a hand-back."""

    assert assess(analyzer, tail).state is not TurnState.COMPLETE


def test_unpunctuated_but_plausible_ending_is_neutral(analyzer):
    assert assess(analyzer, "to put a cache in front of the database").state is (
        TurnState.NEUTRAL
    )


# ---------------------------------------------------------------- ordering


def test_unfinished_sentences_earn_more_silence_than_finished_ones(analyzer):
    unfinished = assess(analyzer, "a trade-off between")
    neutral = assess(analyzer, "a trade-off worth making")
    finished = assess(analyzer, "a trade-off worth making.")

    assert (
        unfinished.silence_threshold_seconds
        > neutral.silence_threshold_seconds
        > finished.silence_threshold_seconds
    )


def test_nothing_said_yet_is_the_most_patient_state(analyzer):
    empty = analyzer.assess("")

    assert empty.state is TurnState.EMPTY
    assert empty.silence_threshold_seconds >= (
        assess(analyzer, "a trade-off between").silence_threshold_seconds
    )


def test_whitespace_only_transcript_counts_as_empty(analyzer):
    assert analyzer.assess("   \n  ").state is TurnState.EMPTY


def test_a_barely_started_answer_gets_extra_patience(analyzer):
    short = analyzer.assess("We used Redis")
    long = analyzer.assess(PREAMBLE + "to use Redis for the hot keys")

    assert short.state is TurnState.NEUTRAL
    assert long.state is TurnState.NEUTRAL
    assert short.silence_threshold_seconds > long.silence_threshold_seconds


def test_a_short_but_clearly_finished_answer_is_not_padded(analyzer):
    """'Yes.' should not be held open just for being short."""

    assessment = analyzer.assess("Yes.")

    assert assessment.state is TurnState.COMPLETE
    assert assessment.silence_threshold_seconds == (
        analyzer.complete_threshold_seconds
    )


def test_thresholds_are_configurable_per_question_type(analyzer):
    # Derived from the default rather than hard-coded, so that retuning the
    # defaults cannot quietly turn this into a comparison against a number
    # that is no longer the more patient of the two.
    patient = TurnCompletenessAnalyzer(
        incomplete_threshold_seconds=(
            analyzer.incomplete_threshold_seconds + 3.0
        )
    )

    assert assess(patient, "a trade-off between").silence_threshold_seconds > (
        assess(analyzer, "a trade-off between").silence_threshold_seconds
    )


def test_every_assessment_explains_itself(analyzer):
    for tail in ["a trade-off between", "a cache.", "a cache, um"]:
        assert assess(analyzer, tail).reason


def test_every_threshold_leaves_room_for_a_thinking_pause(analyzer):
    """
    The two mistakes here are not symmetrical.

    Waiting a second too long after a finished answer is a small
    awkwardness. Cutting in a second too early takes the answer away
    mid-thought and the candidate cannot get it back. So no state may end a
    turn on the kind of pause a person takes mid-sentence.

    The floor was 3.0s, which was overcorrection: a candidate who has
    finished sits in silence long enough to wonder whether anything is
    listening, and reads that as broken rather than as patient. A pause
    taken mid-sentence runs well under a second, so 1.75s still clears it
    with room to spare -- and the candidate is now told in the greeting that
    a pause submits, with a button for anyone who does not want to wait, so
    a shorter floor is no longer the trap it would have been when the wait
    was unannounced.
    """

    for transcript in (
        "That is how I would approach it.",
        "that's it",
        "we scaled it horizontally",
        "a trade-off between",
        "",
    ):
        assessment = assess(analyzer, transcript)

        assert assessment.silence_threshold_seconds >= 1.75, (
            f"{transcript!r} would end the turn after "
            f"{assessment.silence_threshold_seconds}s of silence"
        )
