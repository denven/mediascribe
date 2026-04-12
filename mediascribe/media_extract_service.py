"""Extract or download audio for video inputs."""

import logging
import shutil
import subprocess
from pathlib import Path

from mediascribe.config import MEDIA_SUBDIR
from mediascribe.ffmpeg_utils import convert_audio_to_pcm_wav
from mediascribe.video_models import VideoInput
from mediascribe.yt_dlp_auth import YtDlpAuthOptions, build_yt_dlp_auth_variants

logger = logging.getLogger(__name__)


def extract_audio_for_video(
    video_input: VideoInput,
    output_dir: Path,
    yt_dlp_auth: YtDlpAuthOptions | None = None,
) -> Path:
    """Return a local audio file path suitable for ASR."""

    media_dir = output_dir / MEDIA_SUBDIR
    media_dir.mkdir(parents=True, exist_ok=True)

    if video_input.kind == "local_file":
        return extract_audio_from_local_video(video_input.local_path, media_dir)
    return download_audio_from_url(
        video_input.url,
        media_dir,
        video_input.source_name,
        yt_dlp_auth=yt_dlp_auth,
    )


def extract_audio_from_local_video(video_path: Path, media_dir: Path) -> Path:
    """Extract a mono 16k PCM WAV file from a local video file."""

    target_path = media_dir / f"{video_path.stem}.wav"
    return convert_audio_to_pcm_wav(video_path, target_path)


def download_audio_from_url(
    video_url: str,
    media_dir: Path,
    source_name: str,
    yt_dlp_auth: YtDlpAuthOptions | None = None,
) -> Path:
    """Download and convert the remote video to a local WAV file with yt-dlp."""

    if not shutil.which("yt-dlp"):
        raise EnvironmentError(
            "yt-dlp is required to process remote video URLs.\n"
            "Install it with: uv sync --extra video\n"
            "Fallback options:\n"
            "- process a local video file instead, or\n"
            "- manually obtain subtitles / audio and reuse the existing text or audio summary flows."
        )

    output_template = str(media_dir / f"{source_name}.%(ext)s")
    attempt_details: list[str] = []
    for auth_label, auth_args in build_yt_dlp_auth_variants(yt_dlp_auth):
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-x",
                    "--audio-format",
                    "wav",
                    "--no-playlist",
                    "-o",
                    output_template,
                    *auth_args,
                    video_url,
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode == 0:
                candidates = sorted(media_dir.glob(f"{source_name}.*"))
                for candidate in candidates:
                    if candidate.suffix.lower() == ".wav":
                        return candidate
                if candidates:
                    return candidates[0]
                raise RuntimeError("Audio download completed but no local audio file was created.")

            detail = (result.stderr or result.stdout or "").strip()
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or "").strip()
        attempt_details.append(f"[auth={auth_label}] {detail}" if detail else f"[auth={auth_label}] yt-dlp failed")
        logger.debug(
            "Audio download attempt failed for %s using auth=%s: %s",
            video_url,
            auth_label,
            detail,
        )

    message = (
        "Failed to download audio from the remote video URL with yt-dlp.\n"
        "Try one of these:\n"
        "- retry with a local video file,\n"
        "- use --force-asr or --force-subtitles only when you know the source supports it,\n"
        "- or manually obtain subtitles / audio and reuse the existing pipelines."
    )
    if attempt_details:
        message += "\n\nyt-dlp details:\n" + "\n".join(attempt_details)
    raise RuntimeError(message)
