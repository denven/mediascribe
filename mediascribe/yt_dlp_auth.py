"""Shared yt-dlp authentication option helpers for remote video inputs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class YtDlpAuthOptions:
    site_cookies_file: str | None = None
    cookies_file: str | None = None
    cookies_from_browser: str | None = None


def _parse_site_cookie_map(raw_value: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in raw_value.split(";"):
        entry = item.strip()
        if not entry:
            continue
        domain, sep, cookie_path = entry.partition("=")
        if not sep:
            continue
        domain = domain.strip().lower()
        cookie_path = cookie_path.strip()
        if domain and cookie_path:
            mapping[domain] = cookie_path
    return mapping


def _resolve_site_cookie_file(target_url: str | None) -> str | None:
    if not target_url:
        return None

    host = (urlparse(target_url).hostname or "").lower()
    if not host:
        return None

    mapping = _parse_site_cookie_map(os.environ.get("YTDLP_SITE_COOKIE_MAP", ""))
    if not mapping:
        return None

    for domain, cookie_path in mapping.items():
        if host == domain or host.endswith(f".{domain}"):
            return cookie_path
    return None


def resolve_yt_dlp_auth_options(
    cookies_file: str | None = None,
    cookies_from_browser: str | None = None,
    target_url: str | None = None,
) -> YtDlpAuthOptions:
    """Resolve yt-dlp authentication options from args or environment."""

    resolved = YtDlpAuthOptions(
        site_cookies_file=_resolve_site_cookie_file(target_url),
        cookies_file=(cookies_file or os.environ.get("YTDLP_COOKIES_FILE", "")).strip() or None,
        cookies_from_browser=(cookies_from_browser or os.environ.get("YTDLP_COOKIES_FROM_BROWSER", "")).strip()
        or None,
    )
    return resolved


def build_yt_dlp_auth_variants(
    options: YtDlpAuthOptions | None,
    *,
    include_unauthenticated_fallback: bool = True,
) -> list[tuple[str, list[str]]]:
    """Build ordered yt-dlp auth argument variants."""

    variants: list[tuple[str, list[str]]] = []
    if options is not None:
        if options.site_cookies_file:
            variants.append(("site_cookie_file", ["--cookies", options.site_cookies_file]))
        if options.cookies_file:
            if options.cookies_file != options.site_cookies_file:
                variants.append(("cookie_file", ["--cookies", options.cookies_file]))
        if options.cookies_from_browser:
            variants.append(("browser", ["--cookies-from-browser", options.cookies_from_browser]))

    if include_unauthenticated_fallback or not variants:
        variants.append(("none", []))
    return variants
