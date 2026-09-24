from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar

T = TypeVar("T")

# NOTE: No repository has a concrete implementation yet - the project
# does not currently perform any database access. This interface is
# scaffolding for the architecture's "handlers access the DB behind a
# repository" rule (see app/handlers/), so that when persistence is
# added, handlers depend on this interface rather than a concrete DB
# implementation directly.


class IRepository(ABC, Generic[T]):
    """
    Generic repository contract. Concrete implementations (e.g. a
    SQLAlchemy-backed repository over app/database/) should live
    alongside the models they manage and be provided to handlers via
    dependency injection, mirroring the existing ILogger pattern.
    """

    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        ...

    @abstractmethod
    def create(self, entity: T) -> T:
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        ...

    @abstractmethod
    def delete(self, id: str) -> None:
        ...
