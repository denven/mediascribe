"""Fetch, extract, normalize, and persist subtitles for video inputs."""

import logging
import re
import shutil
import subprocess
from pathlib import Path

from mediascribe.config import SUBTITLES_SUBDIR, SUPPORTED_SUBTITLE_EXTENSIONS
from mediascribe.ffmpeg_utils import check_ffmpeg
from mediascribe.video_models import VideoInput
from mediascribe.yt_dlp_auth import YtDlpAuthOptions, build_yt_dlp_auth_variants

logger = logging.getLogger(__name__)


def fetch_best_subtitle(
    video_input: VideoInput,
    output_dir: Path,
    subtitle_lang: str | None = None,
    yt_dlp_auth: YtDlpAuthOptions | None = None,
) -> Path | None:
    """Return a normalized subtitle text file when a subtitle source is available."""

    if video_input.kind == "local_file":
        subtitle_source = find_local_subtitle_file(video_input.local_path)
        if subtitle_source is None:
            subtitle_source = extract_embedded_subtitle(video_input.local_path, output_dir)
    else:
        subtitle_source = download_url_subtitle(
            video_input.url,
            output_dir,
            subtitle_lang=subtitle_lang,
            yt_dlp_auth=yt_dlp_auth,
        )

    if subtitle_source is None:
        return None
    return normalize_subtitle_file(subtitle_source, output_dir, source_name=video_input.source_name)


def find_local_subtitle_file(video_path: Path) -> Path | None:
    """Return a sibling subtitle file if one exists."""

    for extension in SUPPORTED_SUBTITLE_EXTENSIONS:
        candidate = video_path.with_suffix(extension)
        if candidate.is_file():
            return candidate
    return None


def extract_embedded_subtitle(video_path: Path, output_dir: Path) -> Path | None:
    """Extract the first embedded subtitle track with ffmpeg if present."""

    if not shutil.which("ffmpeg"):
        return None

    check_ffmpeg()
    subtitles_dir = output_dir / SUBTITLES_SUBDIR
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    target_path = subtitles_dir / f"{video_path.stem}.embedded.vtt"

    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-map",
            "0:s:0",
            "-c:s",
            "webvtt",
            str(target_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0 or not target_path.exists():
        logger.debug("No extractable embedded subtitle track found for %s", video_path)
        return None
    return target_path


def download_url_subtitle(
    video_url: str,
    output_dir: Path,
    subtitle_lang: str | None = None,
    yt_dlp_auth: YtDlpAuthOptions | None = None,
) -> Path | None:
    """Download subtitles for a remote video URL with yt-dlp if available."""

    if not shutil.which("yt-dlp"):
        logger.debug(
            "yt-dlp is not installed, skipping remote subtitle fetch. "
            "Install it with `uv sync --extra video` to enable remote subtitle downloads."
        )
        return None

    subtitles_dir = output_dir / SUBTITLES_SUBDIR
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(subtitles_dir / "downloaded_subtitle.%(ext)s")
    last_error = ""
    for auth_label, auth_args in build_yt_dlp_auth_variants(yt_dlp_auth):
        command = [
            "yt-dlp",
            "--skip-download",
            "--write-subs",
            "--write-auto-subs",
            "--convert-subs",
            "srt",
            "--no-playlist",
            "-o",
            out_template,
            *auth_args,
        ]
        if subtitle_lang:
            command.extend(["--sub-langs", subtitle_lang])
        command.append(video_url)

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            candidates = sorted(subtitles_dir.glob("downloaded_subtitle*"))
            if subtitle_lang:
                lang_matches = [path for path in candidates if f".{subtitle_lang}." in path.name]
                if lang_matches:
                    return lang_matches[0]
            return candidates[0] if candidates else None

        last_error = (result.stderr or result.stdout or "").strip()
        logger.debug(
            "Subtitle download attempt failed for %s using auth=%s: %s",
            video_url,
            auth_label,
            last_error,
        )

    logger.debug(
        "Subtitle download failed for %s: %s. The video flow will continue to the audio fallback if available.",
        video_url,
        last_error,
    )
    return None


def normalize_subtitle_file(source_path: Path, output_dir: Path, source_name: str) -> Path:
    """Normalize a subtitle file to transcript-like text and persist it."""

    normalized_text = normalize_subtitle_text(
        source_path.read_text(encoding="utf-8", errors="ignore"),
        format_hint=source_path.suffix.lower(),
    )
    subtitles_dir = output_dir / SUBTITLES_SUBDIR
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    target_path = subtitles_dir / f"{source_name}.subtitle.txt"
    target_path.write_text(normalized_text, encoding="utf-8")
    return target_path


def normalize_subtitle_text(raw_text: str, format_hint: str | None = None) -> str:
    """Convert common subtitle formats into plain summary-ready text."""

    hint = (format_hint or "").lower()
    if hint in {".txt", ".md"}:
        return raw_text.strip()

    lines: list[str] = []
    for original_line in raw_text.splitlines():
        line = original_line.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.upper() == "WEBVTT":
            continue
        if line.startswith("NOTE "):
            continue
        if line in {"Kind: captions", "Kind: subtitles"}:
            continue
        if line.startswith("Language:"):
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if "-->" in line:
            continue
        if line.startswith("[Script Info]") or line.startswith("[V4+ Styles]") or line.startswith("[Events]"):
            continue
        if line.startswith("Format:"):
            continue
        if line.startswith("Dialogue:"):
            line = line.split(",", 9)[-1]

        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"\{\\.*?\}", "", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)

    deduped: list[str] = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped).strip()
