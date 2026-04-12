"""Tests for the scanner module."""

import pytest
from pathlib import Path

from mediascribe.scanner import scan_input


@pytest.fixture
def audio_dir(tmp_path: Path) -> Path:
    """Create a temp directory with mixed files."""
    (tmp_path / "meeting.mp3").touch()
    (tmp_path / "interview.wav").touch()
    (tmp_path / "notes.txt").touch()
    (tmp_path / "photo.jpg").touch()
    (tmp_path / "call.m4a").touch()
    return tmp_path


def test_scan_single_file(tmp_path: Path) -> None:
    audio = tmp_path / "test.mp3"
    audio.touch()
    result = scan_input(str(audio))
    assert result == [audio]


def test_scan_directory(audio_dir: Path) -> None:
    result = scan_input(str(audio_dir))
    names = {f.name for f in result}
    assert names == {"call.m4a", "interview.wav", "meeting.mp3"}


def test_scan_directory_sorted(audio_dir: Path) -> None:
    result = scan_input(str(audio_dir))
    assert result == sorted(result)


def test_scan_nonexistent_path() -> None:
    with pytest.raises(FileNotFoundError):
        scan_input("/nonexistent/path/audio.mp3")


def test_scan_unsupported_format(tmp_path: Path) -> None:
    txt = tmp_path / "notes.txt"
    txt.touch()
    with pytest.raises(ValueError, match="Unsupported audio format"):
        scan_input(str(txt))


def test_scan_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="No supported audio files"):
        scan_input(str(tmp_path))


def test_scan_directory_no_audio(tmp_path: Path) -> None:
    (tmp_path / "readme.md").touch()
    (tmp_path / "data.csv").touch()
    with pytest.raises(ValueError, match="No supported audio files"):
        scan_input(str(tmp_path))


def test_scan_all_supported_formats(tmp_path: Path) -> None:
    extensions = [".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"]
    for ext in extensions:
        (tmp_path / f"audio{ext}").touch()
    result = scan_input(str(tmp_path))
    assert len(result) == len(extensions)
