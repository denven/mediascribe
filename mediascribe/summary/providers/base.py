"""Summary provider base protocol."""

from typing import Protocol

from mediascribe.summary.config import SummaryResult, TextSource


class SummaryProvider(Protocol):
    """Unified interface for summary providers."""

    def summarize(self, text_sources: list[TextSource]) -> SummaryResult:
        """Generate a summary from one or more text sources."""
        ...
