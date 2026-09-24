import logging
from abc import ABC, abstractmethod


class ILogger(ABC):
    """
    Logging contract that services/pipelines/routers depend on.

    Services should never know how logging happens or create their own
    logger instance directly. They receive an ILogger through dependency
    injection.
    """

    @abstractmethod
    def info(self, message: str) -> None:
        ...

    @abstractmethod
    def warning(self, message: str) -> None:
        ...

    @abstractmethod
    def error(self, message: str) -> None:
        ...


class ConsoleLogger(ILogger):
    """
    ILogger implementation that writes to the console using Python's
    standard logging module.
    """

    def __init__(self, name: str = "interview_mirror") -> None:
        self._logger = logging.getLogger(name)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)


_logger_instance = ConsoleLogger()


def get_logger() -> ILogger:
    """
    FastAPI dependency that provides the active ILogger implementation.
    """
    return _logger_instance