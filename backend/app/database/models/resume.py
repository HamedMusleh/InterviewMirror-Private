from sqlalchemy import ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    application_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("applications.id"),
        nullable=False,
        unique=True,
    )

    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    file_data: Mapped[bytes] = mapped_column(
        LargeBinary,
        nullable=False,
    )

    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    personal_information: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    professional_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    skills: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    experience: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    education: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    projects: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    certifications: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    languages: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )