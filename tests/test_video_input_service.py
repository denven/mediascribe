from pathlib import Path

import pytest

from mediascribe.video_input_service import resolve_video_input


def test_resolve_video_input_accepts_local_video_file(tmp_path: Path) -> None:
    video = tmp_path / "lesson.mp4"
    video.write_bytes(b"video")

    result = resolve_video_input(str(video))

    assert result.kind == "local_file"
    assert result.local_path == video
    assert result.source_name == "lesson"


def test_resolve_video_input_accepts_remote_url() -> None:
    result = resolve_video_input("https://example.com/watch/demo-video")

    assert result.kind == "remote_url"
    assert result.url == "https://example.com/watch/demo-video"
    assert result.source_name == "demo-video"


def test_resolve_video_input_rejects_unsupported_extension(tmp_path: Path) -> None:
    video = tmp_path / "lesson.txt"
    video.write_text("nope", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported video format"):
        resolve_video_input(str(video))
