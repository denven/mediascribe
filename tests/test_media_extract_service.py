from pathlib import Path
import subprocess

import pytest

from mediascribe.media_extract_service import download_audio_from_url
from mediascribe.yt_dlp_auth import YtDlpAuthOptions


def test_download_audio_from_url_requires_ytdlp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("mediascribe.media_extract_service.shutil.which", lambda name: None)

    with pytest.raises(EnvironmentError, match="uv sync --extra video"):
        download_audio_from_url("https://example.com/video", tmp_path, "demo")


def test_download_audio_from_url_surfaces_actionable_ytdlp_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("mediascribe.media_extract_service.shutil.which", lambda name: "yt-dlp")

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args[0],
            stderr="network failed",
        )

    monkeypatch.setattr("mediascribe.media_extract_service.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="Failed to download audio from the remote video URL"):
        download_audio_from_url("https://example.com/video", tmp_path, "demo")


def test_download_audio_from_url_passes_cookies_file_to_ytdlp(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("mediascribe.media_extract_service.shutil.which", lambda name: "yt-dlp")
    captured: dict[str, list[str]] = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        (tmp_path / "demo.wav").write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("mediascribe.media_extract_service.subprocess.run", fake_run)

    result = download_audio_from_url(
        "https://example.com/video",
        tmp_path,
        "demo",
        yt_dlp_auth=YtDlpAuthOptions(cookies_file="cookies.txt"),
    )

    assert result == tmp_path / "demo.wav"
    assert "--cookies" in captured["command"]
    assert "cookies.txt" in captured["command"]


def test_download_audio_from_url_falls_back_from_cookie_file_to_browser(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr("mediascribe.media_extract_service.shutil.which", lambda name: "yt-dlp")
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        if len(commands) == 1:
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="cookies file failed")
        (tmp_path / "demo.wav").write_bytes(b"wav")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr("mediascribe.media_extract_service.subprocess.run", fake_run)

    result = download_audio_from_url(
        "https://example.com/video",
        tmp_path,
        "demo",
        yt_dlp_auth=YtDlpAuthOptions(cookies_file="cookies.txt", cookies_from_browser="chrome:Default"),
    )

    assert result == tmp_path / "demo.wav"
    assert "--cookies" in commands[0]
    assert "--cookies-from-browser" in commands[1]
