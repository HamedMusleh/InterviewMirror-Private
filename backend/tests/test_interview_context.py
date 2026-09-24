from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.interview_context import InterviewContextRequest
from app.services.interview_context_service import InterviewContextService


def make_question(
    id,
    interview_id=1,
    sequence_number=1,
    question_text="Explain your experience with FastAPI.",
    question_type="skills",
    skill="FastAPI",
):
    return SimpleNamespace(
        id=id,
        interview_id=interview_id,
        question_text=question_text,
        question_type=question_type,
        skill=skill,
        sequence_number=sequence_number,
    )


def make_answer(question_id, answer_text=None, transcript=None):
    return SimpleNamespace(
        question_id=question_id,
        answer_text=answer_text,
        transcript=transcript,
    )


def make_interview(id=1, application_id=1):
    return SimpleNamespace(id=id, application_id=application_id)


def make_application(id=1, job_opportunity_id=1):
    return SimpleNamespace(id=id, job_opportunity_id=job_opportunity_id)


def make_job_opportunity(id=1, title="Backend Developer"):
    return SimpleNamespace(id=id, title=title)


def make_service(
    question=None,
    previous_questions=None,
    previous_answers=None,
    interview=None,
    application=None,
    job_opportunity=None,
    transcribe_return_value="transcribed answer",
):
    question_repository = MagicMock()
    question_repository.get_by_id.return_value = question
    question_repository.get_by_interview_id.return_value = (
        previous_questions or []
    )

    answer_repository = MagicMock()
    answer_repository.get_by_interview_id.return_value = (
        previous_answers or []
    )

    interview_repository = MagicMock()
    interview_repository.get_by_id.return_value = interview

    application_repository = MagicMock()
    application_repository.get_by_id.return_value = application

    job_opportunity_repository = MagicMock()
    job_opportunity_repository.get_by_id.return_value = job_opportunity

    speech_to_text_service = MagicMock()
    speech_to_text_service.transcribe.return_value = (
        transcribe_return_value
    )

    service = InterviewContextService(
        question_repository=question_repository,
        answer_repository=answer_repository,
        interview_repository=interview_repository,
        application_repository=application_repository,
        job_opportunity_repository=job_opportunity_repository,
        speech_to_text_service=speech_to_text_service,
    )

    return service, speech_to_text_service


def test_request_requires_an_answer_source():
    with pytest.raises(ValidationError):
        InterviewContextRequest(interview_id=4, question_id=25)


def test_request_accepts_answer_text_only():
    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        answer_text="I used FastAPI.",
    )

    assert request.answer_text == "I used FastAPI."


def test_build_context_with_answer_text_matches_canonical_shape():
    question = make_question(id=25, interview_id=4, sequence_number=1)

    service, speech_to_text_service = make_service(
        question=question,
        interview=make_interview(id=4, application_id=1),
        application=make_application(id=1, job_opportunity_id=1),
        job_opportunity=make_job_opportunity(),
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        answer_text=(
            "I used FastAPI to build REST APIs for a university project."
        ),
    )

    context = service.build_context(request)

    assert context.model_dump() == {
        "interview_id": 4,
        "question_id": 25,
        "role": "Backend Developer",
        "question": "Explain your experience with FastAPI.",
        "question_type": "skills",
        "skill": "FastAPI",
        "answer": (
            "I used FastAPI to build REST APIs for a university project."
        ),
        "previous_interactions": [],
    }

    speech_to_text_service.transcribe.assert_not_called()


def test_build_context_runs_stt_when_only_audio_url_given():
    question = make_question(id=25, interview_id=4, sequence_number=1)

    service, speech_to_text_service = make_service(
        question=question,
        interview=make_interview(id=4),
        application=make_application(),
        job_opportunity=make_job_opportunity(),
        transcribe_return_value="I used FastAPI for a university project.",
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        audio_url="https://example.com/answer.webm",
    )

    context = service.build_context(request)

    speech_to_text_service.transcribe.assert_called_once_with(
        "https://example.com/answer.webm"
    )
    assert context.answer == "I used FastAPI for a university project."


def test_build_context_falls_back_to_video_url_for_stt():
    question = make_question(id=25, interview_id=4, sequence_number=1)

    service, speech_to_text_service = make_service(
        question=question,
        interview=make_interview(id=4),
        application=make_application(),
        job_opportunity=make_job_opportunity(),
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        video_url="https://example.com/answer.mp4",
    )

    service.build_context(request)

    speech_to_text_service.transcribe.assert_called_once_with(
        "https://example.com/answer.mp4"
    )


def test_build_context_includes_previous_interactions_in_order():
    current_question = make_question(
        id=26, interview_id=4, sequence_number=2
    )
    previous_question = make_question(
        id=25,
        interview_id=4,
        sequence_number=1,
        question_text="What is dependency injection?",
    )

    service, _ = make_service(
        question=current_question,
        previous_questions=[previous_question, current_question],
        previous_answers=[
            make_answer(
                question_id=25,
                answer_text="A way to provide dependencies at runtime.",
            )
        ],
        interview=make_interview(id=4),
        application=make_application(),
        job_opportunity=make_job_opportunity(),
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=26,
        answer_text="I used FastAPI's Depends system.",
    )

    context = service.build_context(request)

    assert len(context.previous_interactions) == 1
    assert context.previous_interactions[0].question == (
        "What is dependency injection?"
    )
    assert context.previous_interactions[0].answer == (
        "A way to provide dependencies at runtime."
    )


def test_build_context_uses_transcript_when_answer_text_missing_for_prior_turn():
    current_question = make_question(
        id=26, interview_id=4, sequence_number=2
    )
    previous_question = make_question(
        id=25, interview_id=4, sequence_number=1
    )

    service, _ = make_service(
        question=current_question,
        previous_questions=[previous_question, current_question],
        previous_answers=[
            make_answer(question_id=25, transcript="Answered by voice.")
        ],
        interview=make_interview(id=4),
        application=make_application(),
        job_opportunity=make_job_opportunity(),
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=26,
        answer_text="Current answer.",
    )

    context = service.build_context(request)

    assert context.previous_interactions[0].answer == "Answered by voice."


def test_build_context_skips_unanswered_prior_questions():
    current_question = make_question(
        id=26, interview_id=4, sequence_number=2
    )
    previous_question = make_question(
        id=25, interview_id=4, sequence_number=1
    )

    service, _ = make_service(
        question=current_question,
        previous_questions=[previous_question, current_question],
        previous_answers=[],
        interview=make_interview(id=4),
        application=make_application(),
        job_opportunity=make_job_opportunity(),
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=26,
        answer_text="Current answer.",
    )

    context = service.build_context(request)

    assert context.previous_interactions == []


def test_build_context_raises_when_question_not_found():
    service, _ = make_service(question=None)

    request = InterviewContextRequest(
        interview_id=4,
        question_id=99,
        answer_text="Some answer.",
    )

    with pytest.raises(ValueError, match="question 99 not found"):
        service.build_context(request)


def test_build_context_raises_when_question_belongs_to_other_interview():
    question = make_question(id=25, interview_id=999, sequence_number=1)

    service, _ = make_service(question=question)

    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        answer_text="Some answer.",
    )

    with pytest.raises(ValueError, match="does not belong to interview 4"):
        service.build_context(request)


def test_build_context_raises_when_interview_not_found():
    question = make_question(id=25, interview_id=4, sequence_number=1)

    service, _ = make_service(question=question, interview=None)

    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        answer_text="Some answer.",
    )

    with pytest.raises(ValueError, match="Interview 4 not found"):
        service.build_context(request)


def test_build_context_raises_when_application_not_found():
    question = make_question(id=25, interview_id=4, sequence_number=1)

    service, _ = make_service(
        question=question,
        interview=make_interview(id=4, application_id=1),
        application=None,
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        answer_text="Some answer.",
    )

    with pytest.raises(ValueError, match="Application 1 not found"):
        service.build_context(request)


def test_build_context_raises_when_job_opportunity_not_found():
    question = make_question(id=25, interview_id=4, sequence_number=1)

    service, _ = make_service(
        question=question,
        interview=make_interview(id=4, application_id=1),
        application=make_application(id=1, job_opportunity_id=7),
        job_opportunity=None,
    )

    request = InterviewContextRequest(
        interview_id=4,
        question_id=25,
        answer_text="Some answer.",
    )

    with pytest.raises(ValueError, match="Job opportunity 7 not found"):
        service.build_context(request)
