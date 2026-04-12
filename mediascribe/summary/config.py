"""Typed summary configuration models."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextSource:
    name: str
    content: str
    reference: str | None = None


@dataclass(frozen=True)
class SummaryResult:
    content: str
    llm_model: str
    source_names: list[str]
    source_references: list[str] | None = None


@dataclass(frozen=True)
class LitellmSummaryConfig:
    llm_model: str
    api_base: str | None = None


SummaryProviderConfig = LitellmSummaryConfig
