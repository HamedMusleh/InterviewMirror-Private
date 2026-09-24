from sqlalchemy.orm import Session

from app.database.models.resume import Resume
from app.schemas.resume import ResumeSchema


class SQLAlchemyResumeRepository:

    def __init__(self, db: Session):
        self.db = db

    def save(
        self,
        application_id: int,
        file_name: str,
        file_url: str,
        file_type: str,
        file_data: bytes,
        file_size: int,
        resume_data: ResumeSchema,
    ) -> Resume:
        """Add a new resume to the session and flush it.

        Does not commit: the caller owns the transaction. This matters
        for the application-submission flow, where the application row
        and its resume must succeed or fail together.
        """

        db_resume = Resume(
            application_id=application_id,
            file_name=file_name,
            file_url=file_url,
            file_type=file_type,
            file_data=file_data,
            file_size=file_size,
            personal_information=(
                resume_data.personal_information.model_dump()
            ),
            professional_summary=resume_data.professional_summary,
            skills=resume_data.skills.model_dump(),
            experience=[
                experience.model_dump()
                for experience in resume_data.experience
            ],
            education=[
                education.model_dump()
                for education in resume_data.education
            ],
            projects=[
                project.model_dump()
                for project in resume_data.projects
            ],
            certifications=resume_data.certifications,
            languages=resume_data.languages,
        )

        self.db.add(db_resume)
        self.db.flush()
        self.db.refresh(db_resume)

        return db_resume

    def get_by_id(
        self,
        resume_id: int,
    ) -> Resume | None:

        return (
            self.db.query(Resume)
            .filter(Resume.id == resume_id)
            .first()
        )