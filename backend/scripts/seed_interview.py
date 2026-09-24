"""
Create a real interview to answer, so the interview room can be used.

Nothing in the application creates an ``Interview`` row — there is no
interview creation or scheduling endpoint anywhere — so one has to be
inserted directly before the interview room has anything to show. This
inserts the minimal graph the room and the answer flow walk:

    User (recruiter) -> JobOpportunity
    User (candidate) -> Candidate -> Application -> Interview
                                                      -> InterviewQuestion(s)

Deliberately no answers. The point is to answer them out loud, and let the
flow decide whether each one earns a follow-up.

Re-running is safe: it keys off a marker email and prints the existing
interview id if the demo is already there.

    python scripts/seed_interview.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from _speech_env import import_app_modules


import_app_modules()

from app.database.models.application import Application  # noqa: E402
from app.database.models.candidate import Candidate  # noqa: E402
from app.database.models.interview import Interview  # noqa: E402
from app.database.models.interview_question import (  # noqa: E402
    InterviewQuestion,
)
from app.database.models.job_opportunity import JobOpportunity  # noqa: E402
from app.database.models.user import User  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402


CANDIDATE_EMAIL = "demo.candidate@interviewmirror.local"
RECRUITER_EMAIL = "demo.recruiter@interviewmirror.local"
DEMO_JOB_ID = "JD-DEMO-INTERVIEW"


# Open-ended on purpose: these are the questions where a candidate pauses to
# think, which is exactly what the turn detection has to handle well.
QUESTIONS = [
    (
        "Tell me about your experience building APIs with FastAPI.",
        "skills",
        "FastAPI",
    ),
    (
        "How do you decide where a database transaction should begin and end?",
        "skills",
        "PostgreSQL",
    ),
    (
        "Describe a time you had to debug something slow in production.",
        "experience",
        "Debugging",
    ),
]


def seed() -> int:
    session = SessionLocal()

    try:
        existing = session.scalar(
            select(User).where(User.email == CANDIDATE_EMAIL)
        )

        if existing is not None:
            candidate = session.scalar(
                select(Candidate).where(Candidate.user_id == existing.id)
            )
            application = session.scalar(
                select(Application).where(
                    Application.candidate_id == candidate.id
                )
            )
            interview = session.scalar(
                select(Interview).where(
                    Interview.application_id == application.id
                )
            )

            return interview.id

        now = datetime.now(timezone.utc)

        recruiter = User(
            email=RECRUITER_EMAIL,
            password_hash="not-a-real-hash",
            first_name="Riley",
            last_name="Recruiter",
            role="recruiter",
            created_at=now,
            updated_at=now,
            is_active=True,
        )
        candidate_user = User(
            email=CANDIDATE_EMAIL,
            password_hash="not-a-real-hash",
            first_name="Dana",
            last_name="Developer",
            role="candidate",
            created_at=now,
            updated_at=now,
            is_active=True,
        )
        session.add_all([recruiter, candidate_user])
        session.flush()

        candidate = Candidate(
            user_id=candidate_user.id,
            phone="+1-555-0100",
            location="Remote",
            linkedin_url=None,
            github_url=None,
        )
        session.add(candidate)

        job = JobOpportunity(
            job_id=DEMO_JOB_ID,
            recruiter_id=recruiter.id,
            title="Senior Backend Engineer",
            department="Engineering",
            employment_type="full_time",
            location="Remote",
            job_summary=(
                "Build and operate the services behind InterviewMirror's "
                "AI interview pipeline."
            ),
            responsibilities=[
                "Design and ship FastAPI services",
                "Own data models and migrations",
            ],
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            preferred_skills=["SQLAlchemy", "Azure"],
            minimum_years=5,
            experience_level="senior",
            education=["BSc Computer Science or equivalent experience"],
            certifications=[],
            languages=["English"],
            technical_stack=["Python", "FastAPI", "PostgreSQL"],
            soft_skills=["Communication", "Ownership"],
            passing_score=70,
            status="published",
            created_at=now,
            updated_at=now,
        )
        session.add(job)
        session.flush()

        application = Application(
            candidate_id=candidate.id,
            job_opportunity_id=job.id,
            status="interviewing",
            applied_at=now - timedelta(days=7),
            updated_at=now,
        )
        session.add(application)
        session.flush()

        interview = Interview(
            application_id=application.id,
            scheduled_at=now,
            started_at=now,
            ended_at=None,
            status="scheduled",
            created_at=now,
        )
        session.add(interview)
        session.flush()

        for sequence_number, (text, kind, skill) in enumerate(
            QUESTIONS, start=1
        ):
            session.add(
                InterviewQuestion(
                    interview_id=interview.id,
                    question_text=text,
                    question_type=kind,
                    skill=skill,
                    sequence_number=sequence_number,
                    is_follow_up=False,
                    parent_question_id=None,
                    created_at=now,
                )
            )

        session.commit()

        return interview.id
    finally:
        session.close()


if __name__ == "__main__":
    interview_id = seed()

    print("Interview ready.")
    print(f"  interview_id : {interview_id}")
    print(f"  questions    : {len(QUESTIONS)}")
    print()
    print(f"  open http://localhost:5173/interview/{interview_id}")
