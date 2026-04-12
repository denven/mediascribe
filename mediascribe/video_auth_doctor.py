"""Diagnose how remote video auth will be resolved for yt-dlp."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from urllib.parse import urlparse

from mediascribe.runtime import load_environment, setup_logging
from mediascribe.video_input_service import resolve_video_input
from mediascribe.yt_dlp_auth import build_yt_dlp_auth_variants, resolve_yt_dlp_auth_options

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mediascribe doctor-video-auth",
        description="Show how yt-dlp auth will be resolved for a remote video URL.",
    )
    parser.add_argument("input", help="Remote video URL to inspect.")
    parser.add_argument(
        "--yt-dlp-cookies",
        default=None,
        help="Optional cookies.txt override for this diagnostic run.",
    )
    parser.add_argument(
        "--yt-dlp-cookies-from-browser",
        default=None,
        help="Optional browser-cookie override for this diagnostic run.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def build_report_lines(
    input_value: str,
    *,
    yt_dlp_cookies: str | None = None,
    yt_dlp_cookies_from_browser: str | None = None,
) -> list[str]:
    """Return a human-readable diagnostic report."""

    video_input = resolve_video_input(input_value)
    if video_input.kind != "remote_url":
        return [
            "Video auth doctor",
            f"- Input: {input_value}",
            "- Kind: local_file",
            "- yt-dlp auth is not needed for local files.",
        ]

    auth_options = resolve_yt_dlp_auth_options(
        cookies_file=yt_dlp_cookies,
        cookies_from_browser=yt_dlp_cookies_from_browser,
        target_url=video_input.url,
    )
    variants = build_yt_dlp_auth_variants(auth_options)
    host = urlparse(video_input.url).hostname or "(unknown)"

    lines = [
        "Video auth doctor",
        f"- Input: {video_input.url}",
        f"- Host: {host}",
        f"- Source name: {video_input.source_name}",
        f"- Site cookie file: {_format_cookie_path(auth_options.site_cookies_file)}",
        f"- Global cookie file: {_format_cookie_path(auth_options.cookies_file)}",
        f"- Browser cookies: {auth_options.cookies_from_browser or '(not configured)'}",
        "- Auth attempt order:",
    ]
    for index, (label, args) in enumerate(variants, start=1):
        lines.append(f"  {index}. {label}: {_format_variant_args(args)}")
    return lines


def run(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_environment()
    setup_logging(args.verbose)

    for line in build_report_lines(
        args.input,
        yt_dlp_cookies=args.yt_dlp_cookies,
        yt_dlp_cookies_from_browser=args.yt_dlp_cookies_from_browser,
    ):
        logger.info(line)


def _format_cookie_path(path_value: str | None) -> str:
    if not path_value:
        return "(not configured)"
    path = Path(path_value)
    exists = path.exists()
    suffix = "exists" if exists else "missing"
    return f"{path_value} [{suffix}]"


def _format_variant_args(args: list[str]) -> str:
    return " ".join(args) if args else "(no auth args)"
