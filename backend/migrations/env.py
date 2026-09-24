from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.database.base import Base
from app.database.models.application import Application
from app.database.models.candidate_ranking import CandidateRanking
from app.database.models.interview import Interview
from app.database.models.interview_answer import InterviewAnswer
from app.database.models.interview_answer_evaluation import InterviewAnswerEvaluation
from app.database.models.candidate_evaluation import CandidateEvaluation
from app.database.models.interview_question import InterviewQuestion
from app.database.models.job_opportunity import JobOpportunity
from app.database.models.resume import Resume
from app.database.models.screening_criteria import ScreeningCriteria
from app.database.models.screening_result import ScreeningResult
from app.database.models.user import User
from app.database.models.candidate import Candidate
from app.database.session import DATABASE_URL



# Get Alembic configuration
config = context.config

# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the database URL from our application
config.set_main_option(
    "sqlalchemy.url",
    DATABASE_URL.replace("%", "%%"),
)

# Give Alembic access to SQLAlchemy models
target_metadata = Base.metadata


# Run migrations without a direct database connection
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# Run migrations using a database connection
def run_migrations_online() -> None:
    connectable = create_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

# Choose the migration mode
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()