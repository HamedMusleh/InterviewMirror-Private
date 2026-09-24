import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.schemas.adaptive_follow_up import FollowUpQuestionResponse
from app.schemas.answer_analysis import AnswerAnalysis
from app.schemas.interview_context import (
    InterviewContext,
    InterviewContextRequest,
)
from app.services.interview_flow_service import InterviewFlowService


def make_question(
    id=25,
    interview_id=4,
    sequence_number=1,
    question_text="Explain your experience with FastAPI.",
    question_type="skills",
    skill="FastAPI",
    is_follow_up=False,
    parent_question_id=None,
):
    return SimpleNamespace(
        id=id,
        interview_id=interview_id,
        question_text=question_text,
        question_type=question_type,
        skill=skill,
        sequence_number=sequence_number,
        is_follow_up=is_follow_up,
        parent_question_id=parent_question_id,
    )


def make_context(
    interview_id=4,
    question_id=25,
    role="Backend Developer",
    question="Explain your experience with FastAPI.",
    question_type="skills",
    skill="FastAPI",
    answer="I used FastAPI to build REST APIs.",
    previous_interactions=None,
):
    return InterviewContext(
        interview_id=interview_id,
        question_id=question_id,
        role=role,
        question=question,
        question_type=question_type,
        skill=skill,
        answer=answer,
        previous_interactions=previous_interactions or [],
    )


def make_analysis(follow_up_needed, follow_up_reason=None, missing_areas=None):
    return AnswerAnalysis(
        answer_quality="medium",
        relevant_points=["Used FastAPI"],
        missing_areas=missing_areas or [],
        evidence=["I used FastAPI to build REST APIs."],
        follow_up_needed=follow_up_needed,
        follow_up_reason=follow_up_reason,
    )


def make_service(
    context=None,
    current_question=None,
    analysis=None,
    follow_up_response=None,
    stored_follow_up_question=None,
    upcoming_questions=None,
):
    interview_context_service = MagicMock()
    interview_context_service.build_context.return_value = (
        context or make_context()
    )

    answer_analysis_service = MagicMock()
    answer_analysis_service.analyze_answer = AsyncMock(
        return_value=analysis or make_analysis(follow_up_needed=False)
    )

    adaptive_follow_up_service = MagicMock()
    adaptive_follow_up_service.generate_follow_up_question.return_value = (
        follow_up_response
    )

    interview_question_service = MagicMock()
    interview_question_service.store_follow_up_question.return_value = (
        stored_follow_up_question
    )

    question_repository = MagicMock()
    question_repository.get_by_id.return_value = (
        current_question or make_question()
    )
    question_repository.get_by_interview_id.return_value = (
        upcoming_questions or []
    )

    answer_repository = MagicMock()
    interview_repository = MagicMock()

    # Scoring and reporting hang off the end of the answer flow and are not
    # what these tests are about, but the service takes them, so they are
    # mocked wholesale rather than wired.
    evaluation_service = MagicMock()
    # Awaited by the flow, so a plain MagicMock would blow up on `await`.
    evaluation_service.evaluate_answer = AsyncMock()
    evaluation_scoring_service = MagicMock()
    candidate_evaluation_repository = MagicMock()
    candidate_report_service = MagicMock()
    candidate_report_handler = MagicMock()

    service = InterviewFlowService(
        interview_context_service=interview_context_service,
        answer_analysis_service=answer_analysis_service,
        adaptive_follow_up_service=adaptive_follow_up_service,
        interview_question_service=interview_question_service,
        question_repository=question_repository,
        answer_repository=answer_repository,
        interview_repository=interview_repository,
        evaluation_service=evaluation_service,
        evaluation_scoring_service=evaluation_scoring_service,
        candidate_evaluation_repository=candidate_evaluation_repository,
        candidate_report_service=candidate_report_service,
        candidate_report_handler=candidate_report_handler,
    )

    mocks = {
        "interview_context_service": interview_context_service,
        "answer_analysis_service": answer_analysis_service,
        "adaptive_follow_up_service": adaptive_follow_up_service,
        "interview_question_service": interview_question_service,
        "question_repository": question_repository,
        "answer_repository": answer_repository,
        "interview_repository": interview_repository,
    }

    return service, mocks


def make_request(**overrides):
    fields = {
        "interview_id": 4,
        "question_id": 25,
        "answer_text": "I used FastAPI to build REST APIs.",
    }
    fields.update(overrides)
    return InterviewContextRequest(**fields)


def test_persists_the_answer_from_text():
    service, mocks = make_service(
        current_question=make_question(is_follow_up=False),
    )

    asyncio.run(service.submit_answer(make_request()))

    mocks["answer_repository"].create.assert_called_once_with(
        question_id=25,
        answer_text="I used FastAPI to build REST APIs.",
        audio_url=None,
        video_url=None,
        transcript=None,
    )


def test_persists_transcript_when_answer_came_from_audio():
    context = make_context(answer="Transcribed answer text.")

    service, mocks = make_service(
        context=context,
        current_question=make_question(is_follow_up=False),
    )

    request = make_request(
        answer_text=None,
        audio_url="https://example.com/answer.webm",
    )

    asyncio.run(service.submit_answer(request))

    mocks["answer_repository"].create.assert_called_once_with(
        question_id=25,
        answer_text=None,
        audio_url="https://example.com/answer.webm",
        video_url=None,
        transcript="Transcribed answer text.",
    )


def test_follow_up_generated_returns_stored_question():
    stored_question = make_question(
        id=26,
        sequence_number=3,
        is_follow_up=True,
        parent_question_id=25,
        question_text="Can you give a specific example?",
    )

    service, mocks = make_service(
        current_question=make_question(is_follow_up=False),
        analysis=make_analysis(
            follow_up_needed=True,
            follow_up_reason="Answer lacked a concrete example.",
            missing_areas=["specific example"],
        ),
        follow_up_response=FollowUpQuestionResponse(
            parent_question_id=25,
            question="Can you give a specific example?",
            category="skills",
            skill="FastAPI",
        ),
        stored_follow_up_question=stored_question,
    )

    result = asyncio.run(service.submit_answer(make_request()))

    assert result.follow_up_generated is True
    assert result.interview_completed is False
    assert result.next_question.id == 26
    assert result.next_question.is_follow_up is True

    mocks["interview_question_service"].store_follow_up_question.assert_called_once()
    call_kwargs = mocks[
        "interview_question_service"
    ].store_follow_up_question.call_args.kwargs
    assert call_kwargs["interview_id"] == 4
    assert call_kwargs["follow_up"].parent_question_id == 25


def test_no_follow_up_needed_resolves_next_original_question():
    next_question = make_question(id=26, sequence_number=2)

    service, _ = make_service(
        current_question=make_question(id=25, sequence_number=1),
        analysis=make_analysis(follow_up_needed=False),
        upcoming_questions=[
            make_question(id=25, sequence_number=1),
            next_question,
        ],
    )

    result = asyncio.run(service.submit_answer(make_request()))

    assert result.follow_up_generated is False
    assert result.interview_completed is False
    assert result.next_question.id == 26


def test_current_question_is_follow_up_skips_analysis():
    parent_question = make_question(id=25, sequence_number=1)
    follow_up_question = make_question(
        id=26,
        sequence_number=3,
        is_follow_up=True,
        parent_question_id=25,
    )
    next_original_question = make_question(id=27, sequence_number=2)

    service, mocks = make_service(
        current_question=follow_up_question,
        upcoming_questions=[
            parent_question,
            follow_up_question,
            next_original_question,
        ],
    )
    mocks["question_repository"].get_by_id.side_effect = (
        lambda question_id: {
            26: follow_up_question,
            25: parent_question,
        }[question_id]
    )

    request = make_request(question_id=26)
    result = asyncio.run(service.submit_answer(request))

    mocks["answer_analysis_service"].analyze_answer.assert_not_called()
    mocks["adaptive_follow_up_service"].generate_follow_up_question.assert_not_called()
    assert result.follow_up_generated is False
    assert result.next_question.id == 27


def test_no_next_question_marks_interview_completed():
    service, mocks = make_service(
        current_question=make_question(id=25, sequence_number=1),
        analysis=make_analysis(follow_up_needed=False),
        upcoming_questions=[make_question(id=25, sequence_number=1)],
    )

    result = asyncio.run(service.submit_answer(make_request()))

    assert result.follow_up_generated is False
    assert result.next_question is None
    assert result.interview_completed is True
    mocks["interview_repository"].update_status.assert_called_once_with(
        4, "completed"
    )


# --- resuming a reloaded interview -------------------------------------
#
# There is no "current question" column anywhere: progress is derived from
# which questions already have an answer. get_status reports that derived
# position, and answered_count is what lets the interview room tell a
# candidate who reloaded on question three from one who has just arrived --
# the difference between resuming and being walked through the greeting and
# the check-in a second time.


def build_status_service(
    questions,
    answered_ids,
    status="in_progress",
    started_at=None,
    ended_at=None,
):
    """
    Wire only what get_status reads. The rest of the constructor is mocked
    wholesale because none of it is on this path.
    """

    interview = SimpleNamespace(
        id=4,
        status=status,
        started_at=started_at,
        ended_at=ended_at,
    )

    def mark_started(interview_id):
        if interview.started_at is None:
            interview.started_at = datetime.now(timezone.utc)

        return interview.started_at

    interview_repository = MagicMock()
    interview_repository.get_by_id.return_value = interview
    interview_repository.mark_started.side_effect = mark_started

    question_repository = MagicMock()
    question_repository.get_by_interview_id.return_value = questions

    answer_repository = MagicMock()
    answer_repository.get_answered_question_ids.return_value = answered_ids

    return InterviewFlowService(
        interview_context_service=MagicMock(),
        answer_analysis_service=MagicMock(),
        adaptive_follow_up_service=MagicMock(),
        interview_question_service=MagicMock(),
        question_repository=question_repository,
        answer_repository=answer_repository,
        interview_repository=interview_repository,
        evaluation_service=MagicMock(),
        evaluation_scoring_service=MagicMock(),
        candidate_evaluation_repository=MagicMock(),
        candidate_report_service=MagicMock(),
        candidate_report_handler=MagicMock(),
    )


def test_a_fresh_interview_reports_no_answers_yet():
    service = build_status_service(
        questions=[
            make_question(id=25, sequence_number=1),
            make_question(id=26, sequence_number=2),
        ],
        answered_ids=[],
    )

    status = asyncio.run(service.get_status(4))

    assert status.answered_count == 0
    assert status.completed is False
    assert status.next_question.id == 25


def test_a_resumed_interview_reports_how_far_it_got():
    """
    Two answers stored means the candidate is on the third question. The
    room uses the non-zero count to drop them straight back there instead
    of replaying the opening.
    """

    service = build_status_service(
        questions=[
            make_question(id=25, sequence_number=1),
            make_question(id=26, sequence_number=2),
            make_question(id=27, sequence_number=3),
        ],
        answered_ids=[25, 26],
    )

    status = asyncio.run(service.get_status(4))

    assert status.answered_count == 2
    assert status.completed is False
    assert status.next_question.id == 27


def test_an_interview_with_every_question_answered_is_complete():
    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[25],
    )

    status = asyncio.run(service.get_status(4))

    assert status.completed is True
    assert status.next_question is None
    assert status.answered_count == 1


# --- the elapsed clock -------------------------------------------------
#
# The clock is measured on the server and reported as a duration, not left
# to the browser to derive from a timestamp. A candidate whose device clock
# is wrong would otherwise see a wrong or negative timer, and the timer is
# the one thing on screen telling them how long they have been going.


def test_an_unstarted_interview_has_not_begun_counting():
    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[],
        started_at=None,
    )

    status = asyncio.run(service.get_status(4))

    assert status.started_at is None
    assert status.elapsed_seconds == 0


def test_a_running_interview_reports_time_since_it_started():
    started = datetime.now(timezone.utc) - timedelta(minutes=7)

    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[],
        started_at=started,
    )

    status = asyncio.run(service.get_status(4))

    assert status.started_at == started
    # Allow a second of slack for the clock moving during the call.
    assert 419 <= status.elapsed_seconds <= 421


def test_a_finished_interview_freezes_its_clock():
    """
    Otherwise reopening a completed interview shows a timer still climbing
    long after it ended.
    """

    started = datetime.now(timezone.utc) - timedelta(hours=3)
    ended = started + timedelta(minutes=12)

    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[25],
        status="completed",
        started_at=started,
        ended_at=ended,
    )

    status = asyncio.run(service.get_status(4))

    assert status.completed is True
    assert status.elapsed_seconds == 12 * 60


def test_a_clock_that_starts_in_the_future_reads_as_zero():
    """A host clock adjustment must not produce a negative duration."""

    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[],
        started_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )

    status = asyncio.run(service.get_status(4))

    assert status.elapsed_seconds == 0


def test_a_naive_timestamp_is_read_as_utc():
    """
    The column is timezone-aware, but a database or fixture handing back a
    naive datetime must not crash the room with a subtraction error.
    """

    started = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) - timedelta(minutes=2)

    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[],
        started_at=started,
    )

    status = asyncio.run(service.get_status(4))

    assert 119 <= status.elapsed_seconds <= 121


# --- starting the interview -------------------------------------------


def test_starting_an_interview_stamps_the_beginning():
    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[],
        started_at=None,
    )

    status = asyncio.run(service.start(4))

    assert status.started_at is not None


def test_starting_again_does_not_restart_the_clock():
    """
    This is the reload case. The room calls start on every visit, so a
    second call must read the original stamp back rather than overwrite it
    -- overwriting is exactly the bug that made a refresh reset the timer.
    """

    started = datetime.now(timezone.utc) - timedelta(minutes=9)

    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[],
        started_at=started,
    )

    status = asyncio.run(service.start(4))

    assert status.started_at == started
    assert 539 <= status.elapsed_seconds <= 541


def test_starting_a_completed_interview_leaves_it_alone():
    service = build_status_service(
        questions=[make_question(id=25, sequence_number=1)],
        answered_ids=[25],
        status="completed",
        started_at=None,
    )

    status = asyncio.run(service.start(4))

    assert status.completed is True
    assert status.started_at is None


def test_starting_an_interview_that_does_not_exist_is_rejected():
    service = build_status_service(
        questions=[],
        answered_ids=[],
    )

    service.interview_repository.get_by_id.return_value = None

    try:
        asyncio.run(service.start(4))
    except ValueError:
        pass
    else:
        raise AssertionError("expected a ValueError")

