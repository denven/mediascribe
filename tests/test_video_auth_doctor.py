from pathlib import Path

import pytest

from mediascribe.video_auth_doctor import build_report_lines


def test_build_report_lines_for_remote_url(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    site_cookie = tmp_path / "bili.txt"
    global_cookie = tmp_path / "global.txt"
    site_cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")
    global_cookie.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    monkeypatch.setenv(
        "YTDLP_SITE_COOKIE_MAP",
        f"bilibili.com={site_cookie}",
    )
    monkeypatch.setenv("YTDLP_COOKIES_FILE", str(global_cookie))
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "chrome:Profile 12")

    lines = build_report_lines("https://www.bilibili.com/video/BV1VtcYzTEZn/")
    report = "\n".join(lines)

    assert "Host: www.bilibili.com" in report
    assert f"Site cookie file: {site_cookie} [exists]" in report
    assert f"Global cookie file: {global_cookie} [exists]" in report
    assert "Browser cookies: chrome:Profile 12" in report
    assert "1. site_cookie_file: --cookies" in report
    assert "2. cookie_file: --cookies" in report
    assert "3. browser: --cookies-from-browser chrome:Profile 12" in report
    assert "4. none: (no auth args)" in report


def test_build_report_lines_for_local_file(tmp_path: Path) -> None:
    video = tmp_path / "lesson.mp4"
    video.write_bytes(b"video")

    lines = build_report_lines(str(video))

    assert "- Kind: local_file" in lines
    assert "- yt-dlp auth is not needed for local files." in lines
