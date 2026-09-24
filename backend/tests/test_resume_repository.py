from unittest.mock import MagicMock

from app.repositories.resume_repository import SQLAlchemyResumeRepository
from app.schemas.resume import (
    Education,
    Experience,
    PersonalInformation,
    Project,
    ResumeSchema,
    Skills,
)


def _resume_data() -> ResumeSchema:
    return ResumeSchema(
        personal_information=PersonalInformation(
            name="Lina Odeh",
            email="lina@example.com",
            location="Nablus",
        ),
        professional_summary="Backend engineer.",
        skills=Skills(technical=["Python"], tools_and_technologies=["Git"]),
        experience=[
            Experience(job_title="Engineer", company="Acme", years=2)
        ],
        education=[Education(degree="BSc", field="CS")],
        projects=[Project(name="Side project")],
        certifications=["AWS Certified"],
        languages=["Arabic", "English"],
    )


def test_save_persists_the_actual_file_bytes_alongside_parsed_data():
    db = MagicMock()
    repository = SQLAlchemyResumeRepository(db)

    file_bytes = b"%PDF-1.4 fake resume bytes"

    resume = repository.save(
        application_id=100,
        file_name="resume.pdf",
        file_url="",
        file_type="application/pdf",
        file_data=file_bytes,
        file_size=len(file_bytes),
        resume_data=_resume_data(),
    )

    db.add.assert_called_once_with(resume)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(resume)

    assert resume.application_id == 100
    assert resume.file_name == "resume.pdf"
    assert resume.file_type == "application/pdf"
    assert resume.file_data == file_bytes
    assert resume.file_size == len(file_bytes)
    assert resume.personal_information["name"] == "Lina Odeh"
    assert resume.skills["technical"] == ["Python"]
    assert resume.certifications == ["AWS Certified"]


def test_save_does_not_commit_the_transaction():
    """The caller (router) owns the transaction so that application
    creation and resume persistence commit or roll back together."""
    db = MagicMock()
    repository = SQLAlchemyResumeRepository(db)

    repository.save(
        application_id=100,
        file_name="resume.pdf",
        file_url="",
        file_type="application/pdf",
        file_data=b"data",
        file_size=4,
        resume_data=_resume_data(),
    )

    db.commit.assert_not_called()
