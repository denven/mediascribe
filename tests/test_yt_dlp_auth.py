import pytest

from mediascribe.yt_dlp_auth import build_yt_dlp_auth_variants, resolve_yt_dlp_auth_options


def test_resolve_yt_dlp_auth_options_prefers_explicit_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YTDLP_COOKIES_FILE", "env-cookies.txt")
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "edge")

    options = resolve_yt_dlp_auth_options(cookies_file="manual-cookies.txt")

    assert options.site_cookies_file is None
    assert options.cookies_file == "manual-cookies.txt"
    assert options.cookies_from_browser == "edge"
    assert build_yt_dlp_auth_variants(options) == [
        ("cookie_file", ["--cookies", "manual-cookies.txt"]),
        ("browser", ["--cookies-from-browser", "edge"]),
        ("none", []),
    ]


def test_resolve_yt_dlp_auth_options_reads_browser_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "edge:Default")

    options = resolve_yt_dlp_auth_options()

    assert options.site_cookies_file is None
    assert options.cookies_from_browser == "edge:Default"
    assert build_yt_dlp_auth_variants(options) == [
        ("browser", ["--cookies-from-browser", "edge:Default"]),
        ("none", []),
    ]


def test_build_yt_dlp_auth_variants_returns_no_auth_when_unconfigured() -> None:
    assert build_yt_dlp_auth_variants(None) == [("none", [])]


def test_resolve_yt_dlp_auth_options_reads_site_cookie_map(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YTDLP_SITE_COOKIE_MAP", "bilibili.com=.\\cookies\\bili.txt;youtube.com=.\\cookies\\yt.txt")
    monkeypatch.setenv("YTDLP_COOKIES_FILE", ".\\cookies\\global.txt")
    monkeypatch.setenv("YTDLP_COOKIES_FROM_BROWSER", "chrome:Profile 12")

    options = resolve_yt_dlp_auth_options(
        target_url="https://www.bilibili.com/video/BV1VtcYzTEZn/",
    )

    assert options.site_cookies_file == ".\\cookies\\bili.txt"
    assert options.cookies_file == ".\\cookies\\global.txt"
    assert options.cookies_from_browser == "chrome:Profile 12"
    assert build_yt_dlp_auth_variants(options) == [
        ("site_cookie_file", ["--cookies", ".\\cookies\\bili.txt"]),
        ("cookie_file", ["--cookies", ".\\cookies\\global.txt"]),
        ("browser", ["--cookies-from-browser", "chrome:Profile 12"]),
        ("none", []),
    ]
