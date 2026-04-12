"""File discovery: validate paths and filter audio files by extension."""

import logging
from pathlib import Path

from mediascribe.config import SUPPORTED_AUDIO_EXTENSIONS

logger = logging.getLogger(__name__)


def scan_input(input_path: str) -> list[Path]:
    """Return a list of audio file paths from a file or directory path.

    For a file path, validates it exists and has a supported extension.
    For a directory, scans top-level files (non-recursive) and filters by extension.

    Raises:
        FileNotFoundError: If the input path does not exist.
        ValueError: If a single file has an unsupported extension.
        ValueError: If a directory contains no supported audio files.
    """
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        _validate_audio_extension(path)
        return [path]

    if path.is_dir():
        audio_files = sorted(
            f for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        )
        if not audio_files:
            raise ValueError(
                f"No supported audio files found in directory: {path}\n"
                f"Supported formats: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}"
            )
        logger.info("Found %d audio file(s) in %s", len(audio_files), path)
        return audio_files

    raise ValueError(f"Input path is neither a file nor a directory: {path}")


def _validate_audio_extension(path: Path) -> None:
    """Raise ValueError if the file extension is not supported."""
    if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format: {path.suffix}\n"
            f"Supported formats: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}"
        )
