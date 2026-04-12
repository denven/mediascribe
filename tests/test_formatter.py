"""Tests for the formatter module."""

from pathlib import Path

from mediascribe.formatter import (
    apply_speaker_names,
    format_timestamp,
    format_transcript,
    write_transcript,
)
from mediascribe.models import TranscribedSegment


def test_format_timestamp_zero() -> None:
    assert format_timestamp(0.0) == "[00:00:00]"


def test_format_timestamp_seconds() -> None:
    assert format_timestamp(45.0) == "[00:00:45]"


def test_format_timestamp_minutes() -> None:
    assert format_timestamp(125.0) == "[00:02:05]"


def test_format_timestamp_hours() -> None:
    assert format_timestamp(3661.0) == "[01:01:01]"


def test_apply_speaker_names_replaces_by_first_appearance() -> None:
    segments = [
        TranscribedSegment(start=0.0, end=3.0, speaker="Speaker 2", text="Hello"),
        TranscribedSegment(start=5.0, end=8.0, speaker="Speaker 1", text="Hi there"),
        TranscribedSegment(start=9.0, end=11.0, speaker="Speaker 2", text="Again"),
    ]

    result = apply_speaker_names(segments, ["Alice", "Bob"])

    assert result[0].speaker == "Alice"
    assert result[1].speaker == "Bob"
    assert result[2].speaker == "Alice"


def test_apply_speaker_names_leaves_unmapped_speakers_in_place() -> None:
    segments = [
        TranscribedSegment(start=0.0, end=3.0, speaker="Speaker 1", text="Hello"),
        TranscribedSegment(start=5.0, end=8.0, speaker="Speaker 2", text="Hi there"),
        TranscribedSegment(start=9.0, end=12.0, speaker="Unknown", text="Noise"),
    ]

    result = apply_speaker_names(segments, ["Alice"])

    assert result[0].speaker == "Alice"
    assert result[1].speaker == "Speaker 2"
    assert result[2].speaker == "Unknown"


def test_format_transcript_content() -> None:
    segments = [
        TranscribedSegment(start=0.0, end=3.0, speaker="Speaker 1", text="Hello"),
        TranscribedSegment(start=5.0, end=8.0, speaker="Speaker 2", text="Hi there"),
    ]
    result = format_transcript(segments, "test.mp3")

    assert "=== test.mp3 ===" in result
    assert "Transcribed:" in result
    assert "[00:00:00] Speaker 1: Hello" in result
    assert "[00:00:05] Speaker 2: Hi there" in result


def test_format_transcript_empty_segments() -> None:
    result = format_transcript([], "empty.mp3")
    assert "=== empty.mp3 ===" in result


def test_write_transcript(tmp_path: Path) -> None:
    text = "[00:00:00] Speaker 1: Test content"
    path = write_transcript(text, "meeting.mp3", tmp_path)

    assert path.exists()
    assert path.name == "meeting.txt"
    assert path.parent.name == "transcripts"
    assert path.read_text(encoding="utf-8") == text
