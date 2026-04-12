"""Copyable example of a custom summary provider.

This file is not auto-discovered where it currently lives.
To enable it, copy it into `mediascribe/summary/providers/`.
"""

from __future__ import annotations

from dataclasses import dataclass

from mediascribe.summary.config import SummaryResult, TextSource
from mediascribe.summary.registry import register_summary_provider


@dataclass(frozen=True)
class MockSummaryConfig:
    prefix: str = "mock-summary"


class MockSummaryProvider:
    """Minimal example provider that synthesizes a deterministic summary."""

    def __init__(self, config: MockSummaryConfig) -> None:
        self._prefix = config.prefix

    def summarize(self, text_sources: list[TextSource]) -> SummaryResult:
        source_names = [source.name for source in text_sources]
        preview = "; ".join(source.content[:24] for source in text_sources)
        # Real LLM / HTTP integration usually looks like this:
        # 1. Combine `text_sources` into your prompt or request body
        # 2. Call the remote API or local model
        # 3. Convert the response text into `SummaryResult`
        #
        # Example sketch:
        #
        # prompt = "\\n\\n---\\n\\n".join(source.content for source in text_sources)
        # response = client.responses.create(
        #     model="your-model",
        #     input=prompt,
        # )
        # summary_text = response.output_text
        # return SummaryResult(
        #     content=summary_text,
        #     llm_model="your-provider/your-model",
        #     source_names=source_names,
        # )
        return SummaryResult(
            content=f"{self._prefix}: {preview}",
            llm_model="mock/provider-v1",
            source_names=source_names,
        )


def resolve_mock_summary_runtime(*, llm_model: str | None = None) -> MockSummaryConfig | None:
    """Route matching model names to this provider."""

    # Keep the routing check small and explicit so providers do not claim
    # requests that should be handled by other summary backends.
    if llm_model and not llm_model.startswith("mock/"):
        return None
    return MockSummaryConfig(prefix=llm_model or "mock-summary")


register_summary_provider(
    "mock-summary",
    MockSummaryProvider,
    runtime_resolver=resolve_mock_summary_runtime,
)
