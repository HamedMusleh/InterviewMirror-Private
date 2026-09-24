from sqlalchemy import DateTime, Integer, String, Text

from app.database.base import Base
from app.database.models.interview import Interview
from app.database.models.interview_answer import InterviewAnswer


def test_interview_table_matches_the_agreed_schema():
    table = Interview.__table__

    assert table.name == "interviews"
    assert isinstance(table.c.id.type, Integer)
    assert isinstance(table.c.application_id.type, Integer)
    assert isinstance(table.c.status.type, String)
    assert table.c.status.type.length == 50
    assert table.c.application_id.nullable is False
    assert table.c.scheduled_at.nullable is False
    assert table.c.started_at.nullable is True
    assert table.c.ended_at.nullable is True
    assert table.c.created_at.nullable is False
    assert isinstance(table.c.scheduled_at.type, DateTime)
    assert table.c.scheduled_at.type.timezone is True
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    application_targets = {
        str(foreign_key.target_fullname)
        for foreign_key in table.c.application_id.foreign_keys
    }
    assert application_targets == {
        "applications.id"
    }


def test_interview_answer_table_matches_the_agreed_schema():
    table = InterviewAnswer.__table__

    assert table.name == "interview_answers"
    assert isinstance(table.c.id.type, Integer)
    assert isinstance(table.c.question_id.type, Integer)
    assert isinstance(table.c.answer_text.type, Text)
    assert isinstance(table.c.audio_url.type, String)
    assert table.c.audio_url.type.length == 500
    assert isinstance(table.c.video_url.type, String)
    assert table.c.video_url.type.length == 500
    assert isinstance(table.c.transcript.type, Text)
    assert table.c.question_id.nullable is False
    assert table.c.answer_text.nullable is True
    assert table.c.audio_url.nullable is True
    assert table.c.video_url.nullable is True
    assert table.c.transcript.nullable is True
    assert table.c.answered_at.nullable is False
    assert isinstance(table.c.answered_at.type, DateTime)
    assert table.c.answered_at.type.timezone is True
    assert table.c.answered_at.default is not None
    assert callable(table.c.answered_at.default.arg)
    question_targets = {
        str(foreign_key.target_fullname)
        for foreign_key in table.c.question_id.foreign_keys
    }
    assert question_targets == {
        "interview_questions.id"
    }
    assert "ck_interview_answers_has_content" in {
        constraint.name for constraint in table.constraints
    }


def test_interview_models_are_registered_with_the_shared_metadata():
    assert Base.metadata.tables["interviews"] is Interview.__table__
    assert Base.metadata.tables["interview_answers"] is InterviewAnswer.__table__
