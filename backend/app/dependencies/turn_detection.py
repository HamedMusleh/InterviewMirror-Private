"""Providers for the live turn-detection feature."""

from functools import lru_cache

from app.services.turn_completeness_service import TurnCompletenessAnalyzer


@lru_cache
def get_turn_completeness_analyzer() -> TurnCompletenessAnalyzer:
    """
    Build the shared analyzer.

    It holds no per-request state — it is a pure function over a transcript —
    so one instance serves every connection.
    """

    return TurnCompletenessAnalyzer()
