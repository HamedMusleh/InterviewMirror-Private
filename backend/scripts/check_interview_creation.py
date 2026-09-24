"""
End-to-end check for creating an interview for an accepted candidate.

Seeds the graph the endpoint reads (User -> Candidate -> Application, plus a
recruiter and a job, and a screening result), then drives
``POST /api/interviews`` against a running server and reads the database back
to confirm what was actually written.

Every branch is exercised, not just the happy path, because most of the
endpoint's job is refusing to create interviews it should not:

    recommended        -> 201, a new scheduled interview
    same application   -> 200, the same interview, created=false
    not recommended    -> 409
    never screened     -> 409
    unknown            -> 404

Start the backend first, then:

    python scripts/check_interview_creation.py
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select

from _speech_env import import_app_modules


import_app_modules()

from app.database.models.application import Application  # noqa: E402
from app.database.models.candidate import Candidate  # noqa: E402
from app.database.models.interview import Interview  # noqa: E402
from app.database.models.interview_answer import (  # noqa: E402
    InterviewAnswer,
)
from app.database.models.interview_question import (  # noqa: E402
    InterviewQuestion,
)
from app.database.models.job_opportunity import JobOpportunity  # noqa: E402
from app.database.models.screening_criteria import (  # noqa: E402
    ScreeningCriteria,
)
from app.database.models.screening_result import ScreeningResult  # noqa: E402
from app.database.models.user import User  # noqa: E402
from app.database.session import SessionLocal  # noqa: E402


BASE_URL = "http://127.0.0.1:8000"

MARKER = "interview-creation-check"
RECRUITER_EMAIL = f"{MARKER}.recruiter@interviewmirror.local"
JOB_ID = "JD-INTERVIEW-CREATION-CHECK"


def post(path: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        body = error.read()

        try:
            return error.code, json.loads(body)
        except ValueError:
            return error.code, {"detail": body.decode()[:200]}


def reset(session) -> None:
    """Remove anything a previous run of this check left behind."""

    users = session.scalars(
        select(User).where(User.email.like(f"%{MARKER}%"))
    ).all()

    candidate_ids = [
        candidate.id
        for candidate in session.scalars(
            select(Candidate).where(
                Candidate.user_id.in_([user.id for user in users] or [0])
            )
        ).all()
    ]

    application_ids = [
        application.id
        for application in session.scalars(
            select(Application).where(
                Application.candidate_id.in_(candidate_ids or [0])
            )
        ).all()
    ]

    if application_ids:
        # Interviews now carry generated questions, so the children have to
        # go first or the delete trips the foreign key.
        interview_ids = [
            interview.id
            for interview in session.scalars(
                select(Interview).where(
                    Interview.application_id.in_(application_ids)
                )
            ).all()
        ]

        if interview_ids:
            question_ids = [
                question.id
                for question in session.scalars(
                    select(InterviewQuestion).where(
                        InterviewQuestion.interview_id.in_(interview_ids)
                    )
                ).all()
            ]

            if question_ids:
                session.execute(
                    delete(InterviewAnswer).where(
                        InterviewAnswer.question_id.in_(question_ids)
                    )
                )

            session.execute(
                delete(InterviewQuestion).where(
                    InterviewQuestion.interview_id.in_(interview_ids)
                )
            )

        session.execute(
            delete(Interview).where(
                Interview.application_id.in_(application_ids)
            )
        )
        session.execute(
            delete(ScreeningResult).where(
                ScreeningResult.application_id.in_(application_ids)
            )
        )
        session.execute(
            delete(Application).where(Application.id.in_(application_ids))
        )

    if candidate_ids:
        session.execute(delete(Candidate).where(Candidate.id.in_(candidate_ids)))

    job = session.scalar(
        select(JobOpportunity).where(JobOpportunity.job_id == JOB_ID)
    )

    if job is not None:
        session.execute(
            delete(ScreeningCriteria).where(
                ScreeningCriteria.job_id == job.id
            )
        )

    session.execute(
        delete(JobOpportunity).where(JobOpportunity.job_id == JOB_ID)
    )
    session.execute(delete(User).where(User.email.like(f"%{MARKER}%")))
    session.commit()


def seed(session) -> dict[str, int]:
    """Create three applications: recommended, rejected, and unscreened."""

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
    session.add(recruiter)
    session.flush()

    job = JobOpportunity(
        job_id=JOB_ID,
        recruiter_id=recruiter.id,
        title="Senior Backend Engineer",
        department="Engineering",
        employment_type="full_time",
        location="Remote",
        job_summary="Checking interview creation for accepted candidates.",
        responsibilities=["Ship services"],
        required_skills=["Python", "FastAPI"],
        preferred_skills=["Azure"],
        minimum_years=5,
        experience_level="senior",
        education=["BSc Computer Science"],
        certifications=[],
        languages=["English"],
        technical_stack=["Python"],
        soft_skills=["Communication"],
        passing_score=70,
        status="published",
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.flush()

    # Shaped as the screening module stores it: the generated criteria
    # live under a "screening_criteria" key, and question generation reads
    # them straight back out.
    criteria = ScreeningCriteria(
        job_id=job.id,
        criteria={
            "job_id": JOB_ID,
            "passing_score": 70,
            "screening_criteria": {
                "skills": {
                    "weight": 40,
                    "required": [
                        {"name": "Python", "weight": 20},
                        {"name": "FastAPI", "weight": 20},
                    ],
                    "preferred": [{"name": "Azure", "weight": 5}],
                },
                "experience": {
                    "weight": 25,
                    "minimum_years": 5,
                    "level": "senior",
                },
                "education": {
                    "weight": 10,
                    "preferred_fields": ["Computer Science"],
                },
                "projects": {
                    "weight": 10,
                    "required": True,
                    "relevant_domains": ["Backend"],
                },
                "certifications": {"weight": 5, "criteria": []},
                "languages": {"weight": 5, "criteria": ["English"]},
                "soft_skills": {
                    "weight": 5,
                    "criteria": ["Communication"],
                },
            },
        },
        created_at=now,
        updated_at=now,
    )
    session.add(criteria)
    session.flush()

    applications: dict[str, int] = {}

    for label, final_status, score in (
        ("recommended", "recommended", 88.0),
        ("rejected", "not_recommended", 41.0),
        ("unscreened", None, None),
    ):
        user = User(
            email=f"{MARKER}.{label}@interviewmirror.local",
            password_hash="not-a-real-hash",
            first_name=label.capitalize(),
            last_name="Candidate",
            role="candidate",
            created_at=now,
            updated_at=now,
            is_active=True,
        )
        session.add(user)
        session.flush()

        candidate = Candidate(user_id=user.id, location="Remote")
        session.add(candidate)
        session.flush()

        application = Application(
            candidate_id=candidate.id,
            job_opportunity_id=job.id,
            status="screened",
            applied_at=now - timedelta(days=2),
            updated_at=now,
        )
        session.add(application)
        session.flush()

        applications[label] = application.id

        if final_status is not None:
            session.add(
                ScreeningResult(
                    application_id=application.id,
                    criteria_id=criteria.id,
                    overall_score=score,
                    passing_score=70.0,
                    confidence_score=0.9,
                    final_status=final_status,
                    category_breakdown={},
                    # Lists, matching what the screening service writes.
                    matched_criteria=["skills"],
                    missing_criteria=[],
                    matching_details={},
                    created_at=now,
                )
            )

    session.commit()

    return applications


def report(label: str, expected: int, status: int, body: dict) -> bool:
    ok = status == expected
    mark = "PASS" if ok else "FAIL"

    print(f"  [{mark}] {label:<38} expected {expected}, got {status}")

    if not ok:
        print(f"         {json.dumps(body)[:180]}")

    return ok


def main() -> int:
    try:
        urllib.request.urlopen(f"{BASE_URL}/api/status", timeout=5)
    except Exception:
        print(f"The backend is not answering on {BASE_URL}.")
        print("Start it first:  python -m uvicorn app.main:app --port 8000")
        return 1

    session = SessionLocal()

    try:
        reset(session)
        applications = seed(session)

        print("Seeded applications:")
        for label, application_id in applications.items():
            print(f"  {label:<12} application_id={application_id}")
        print()

        failures = 0

        print("Endpoint behaviour:")

        status, body = post(
            "/api/interviews", {"application_id": applications["recommended"]}
        )
        failures += not report("recommended -> creates", 201, status, body)

        created_id = body.get("interview", {}).get("id")
        was_created = body.get("created")

        if created_id is None or was_created is not True:
            print("         expected created=true and an interview id")
            failures += 1

        status, body = post(
            "/api/interviews", {"application_id": applications["recommended"]}
        )
        failures += not report("same application -> no duplicate", 200, status, body)

        if body.get("created") is not False:
            print("         expected created=false on the retry")
            failures += 1

        if body.get("interview", {}).get("id") != created_id:
            print("         retry returned a different interview")
            failures += 1

        status, body = post(
            "/api/interviews", {"application_id": applications["rejected"]}
        )
        failures += not report("not recommended -> refused", 409, status, body)

        status, body = post(
            "/api/interviews", {"application_id": applications["unscreened"]}
        )
        failures += not report("never screened -> refused", 409, status, body)

        status, body = post("/api/interviews", {"application_id": 99999999})
        failures += not report("unknown application -> 404", 404, status, body)

        status, body = post("/api/interviews", {"application_id": 0})
        failures += not report("invalid id -> rejected", 422, status, body)

        status, body = post(
            "/api/interviews",
            {
                "application_id": applications["unscreened"],
                "scheduled_at": "2026-09-10T10:00:00",
            },
        )
        failures += not report("naive timestamp -> rejected", 422, status, body)

        # --- what actually landed in the database -----------------------
        print()
        print("Database:")

        session.expire_all()

        rows = session.scalars(
            select(Interview).where(
                Interview.application_id.in_(applications.values())
            )
        ).all()

        print(f"  interviews created: {len(rows)} (expected exactly 1)")

        if len(rows) != 1:
            failures += 1

        for row in rows:
            print(
                f"    id={row.id} application_id={row.application_id} "
                f"status={row.status!r}"
            )
            print(f"    scheduled_at={row.scheduled_at}")
            print(f"    started_at={row.started_at} ended_at={row.ended_at}")

            if row.status != "scheduled":
                print("    status should be 'scheduled'")
                failures += 1

            if row.application_id != applications["recommended"]:
                print("    linked to the wrong application")
                failures += 1

        print()

        if failures:
            print(f"{failures} CHECK(S) FAILED")
            return 1

        print("ALL CHECKS PASSED")
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
