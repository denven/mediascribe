"""Resolve local video files and remote video URLs into a common input model."""

from pathlib import Path
from urllib.parse import urlparse

from mediascribe.config import SUPPORTED_VIDEO_EXTENSIONS
from mediascribe.video_models import VideoInput


def resolve_video_input(input_value: str) -> VideoInput:
    """Return a normalized video input description for a file path or URL."""

    if _looks_like_url(input_value):
        return VideoInput(
            raw_input=input_value,
            kind="remote_url",
            source_name=_source_name_from_url(input_value),
            url=input_value,
        )

    path = Path(input_value)
    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Video input must be a file path or URL: {path}")
    if path.suffix.lower() not in SUPPORTED_VIDEO_EXTENSIONS:
        raise ValueError(
            f"Unsupported video format: {path.suffix}\n"
            f"Supported formats: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}"
        )
    return VideoInput(
        raw_input=input_value,
        kind="local_file",
        source_name=path.stem,
        local_path=path,
    )


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _source_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).stem or parsed.netloc
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in candidate)
    return cleaned.strip("-") or "video"
