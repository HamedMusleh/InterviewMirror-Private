from typing import Protocol


class LoggerInterface(Protocol):

    def info(self, message: str) -> None:
        ...

    def exception(self, message: str) -> None:
        ...