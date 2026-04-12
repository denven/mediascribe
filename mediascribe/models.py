"""Shared data models used across all ASR providers and downstream modules."""

from dataclasses import dataclass


@dataclass
class TranscribedSegment:
    """A transcript segment with speaker label and timing — the unified output of all ASR providers."""
    start: float   # seconds
    end: float     # seconds
    speaker: str   # e.g. "Speaker 1"
    text: str
