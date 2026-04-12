from pathlib import Path
import subprocess

import pytest

from mediascribe.subtitle_fetch_service import (
    download_url_subtitle,
    find_local_subtitle_file,
    normalize_subtitle_text,
)
from mediascribe.yt_dlp_auth import YtDlpAuthOptions


def test_find_local_subtitle_file_prefers_same_stem(tmp_path: Path) -> None:
    video = tmp_path / "lesson.mp4"
    subtitle = tmp_path / "lesson.srt"
    video.write_bytes(b"video")
    subtitle.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")

    assert find_local_subtitle_file(video) == subtitle


def test_normalize_subtitle_text_removes_timestamps_and_duplicates() -> None:
    raw = """WEBVTT

1
00:00:00.000 --> 00:00:01.000
Hello

2
00:00:01.000 --> 00:00:02.000
Hello

3
00:00:02.000 --> 00:00:03.000
World
"""

    assert normalize_subtitle_text(raw, format_hint=".vtt") == "Hello\nWorld"


def test_normalize_subtitle_text_handles_ass_dialogue_lines() -> None:
    raw = """[Events]
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\\an8}Hi there
Dialogue: 0,0:00:02.00,0:00:03.00,Default,,0,0,0,,<i>General Kenobi</i>
"""

    assert normalize_subtitle_text(raw, format_hint=".ass") == "Hi there\nGeneral Kenobi"


def test_download_url_subtitle_passes_browser_cookies_to_ytdlp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("mediascribe.subtitle_fetch_service.shutil.which", lambda name: "yt-dlp")
    captured: dict[str, list[str]] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        target = tmp_path / "subtitles" / "downloaded_subtitle.en.srt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("mediascribe.subtitle_fetch_service.subprocess.run", fake_run)

    result = download_url_subtitle(
        "https://example.com/video",
        tmp_path,
        subtitle_lang="en",
        yt_dlp_auth=YtDlpAuthOptions(cookies_from_browser="edge:Default"),
    )

    assert result == tmp_path / "subtitles" / "downloaded_subtitle.en.srt"
    assert "--cookies-from-browser" in captured["command"]
    assert "edge:Default" in captured["command"]


def test_download_url_subtitle_falls_back_from_cookie_file_to_browser(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("mediascribe.subtitle_fetch_service.shutil.which", lambda name: "yt-dlp")
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if len(commands) == 1:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="cookies file failed")
        target = tmp_path / "subtitles" / "downloaded_subtitle.en.srt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("1\n00:00:00,000 --> 00:00:01,000\nHello\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("mediascribe.subtitle_fetch_service.subprocess.run", fake_run)

    result = download_url_subtitle(
        "https://example.com/video",
        tmp_path,
        subtitle_lang="en",
        yt_dlp_auth=YtDlpAuthOptions(cookies_file="cookies.txt", cookies_from_browser="chrome:Default"),
    )

    assert result == tmp_path / "subtitles" / "downloaded_subtitle.en.srt"
    assert "--cookies" in commands[0]
    assert "--cookies-from-browser" in commands[1]
