"""Shared models for the video summary input layer."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoInput:
    raw_input: str
    kind: str
    source_name: str
    local_path: Path | None = None
    url: str | None = None


@dataclass(frozen=True)
class VideoSummaryResult:
    summary_path: Path | None
    strategy_used: str
    subtitle_path: Path | None = None
    audio_path: Path | None = None
    transcript_paths: list[Path] | None = None
