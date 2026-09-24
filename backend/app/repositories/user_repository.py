from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models.user import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(
        self,
        user_id: int,
    ) -> User | None:
        statement = select(User).where(
            User.id == user_id
        )

        return self.db.scalar(statement)

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        statement = select(User).where(
            User.email == email
        )

        return self.db.scalar(statement)

    def create(
        self,
        email: str,
        first_name: str,
        last_name: str,
        password_hash: str,
        role: str,
    ) -> User:
        """Add a new user to the session and flush it.

        Does not commit: user creation is one step of the larger
        candidate-resolution flow (see ApplicationService), so the
        caller owns the transaction and commits once every step
        succeeds.
        """

        now = datetime.now(timezone.utc)

        user = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            role=role,
            created_at=now,
            updated_at=now,
            is_active=True,
        )

        self.db.add(user)
        self.db.flush()

        return user
