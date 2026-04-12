"""Shared ffmpeg helpers for media preprocessing."""

import json
import logging
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass
from contextlib import closing
from pathlib import Path

logger = logging.getLogger(__name__)

MIN_FFMPEG_VERSION = (4, 4)


def check_ffmpeg() -> None:
    """Verify ffmpeg is installed and meets the minimum version requirement."""

    if not shutil.which("ffmpeg"):
        raise EnvironmentError(
            "ffmpeg is not found in PATH. It is required for audio decoding.\n"
            "Install: https://ffmpeg.org/download.html"
        )

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        match = re.search(r"ffmpeg version (\d+)\.(\d+)", result.stdout)
        if match:
            major, minor = int(match.group(1)), int(match.group(2))
            if (major, minor) < MIN_FFMPEG_VERSION:
                raise EnvironmentError(
                    "ffmpeg %d.%d is too old. Minimum required: %d.%d\n"
                    "Download: https://ffmpeg.org/download.html"
                    % (major, minor, *MIN_FFMPEG_VERSION)
                )
            logger.debug("ffmpeg version: %d.%d", major, minor)
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.warning("Could not determine ffmpeg version: %s", exc)


def convert_audio_to_pcm_wav(
    source_path: Path,
    target_path: Path,
    *,
    sample_rate: int = 16000,
    channels: int = 1,
    timeout: int = 300,
) -> Path:
    """Convert audio or video media into mono PCM WAV for downstream ASR."""

    check_ffmpeg()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        str(target_path),
    ]

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        if detail:
            raise RuntimeError(
                f"ffmpeg failed to convert '{source_path.name}' to PCM WAV: {detail}"
            ) from exc
        raise RuntimeError(
            f"ffmpeg failed to convert '{source_path.name}' to PCM WAV."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"ffmpeg timed out while converting '{source_path.name}' to PCM WAV."
        ) from exc

    return target_path


@dataclass(frozen=True)
class AudioMediaInfo:
    """Basic audio media facts used for ASR safety checks."""

    size_bytes: int
    duration_seconds: float | None
    sample_rate: int | None = None
    channels: int | None = None


def inspect_audio_media(source_path: Path) -> AudioMediaInfo:
    """Return basic duration/size details for a local audio file."""

    size_bytes = source_path.stat().st_size

    if source_path.suffix.lower() == ".wav":
        try:
            with closing(wave.open(str(source_path), "rb")) as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                duration = frames / float(sample_rate) if sample_rate else None
                return AudioMediaInfo(
                    size_bytes=size_bytes,
                    duration_seconds=duration,
                    sample_rate=sample_rate,
                    channels=channels,
                )
        except (wave.Error, OSError):
            logger.debug("Failed to inspect WAV header for %s, falling back to ffprobe", source_path)

    check_ffmpeg()
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=sample_rate,channels",
                "-of",
                "json",
                str(source_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("Failed to inspect %s with ffprobe: %s", source_path, exc)
        return AudioMediaInfo(size_bytes=size_bytes, duration_seconds=None)

    payload = json.loads(result.stdout or "{}")
    stream = (payload.get("streams") or [{}])[0]
    duration_raw = (payload.get("format") or {}).get("duration")

    return AudioMediaInfo(
        size_bytes=size_bytes,
        duration_seconds=float(duration_raw) if duration_raw else None,
        sample_rate=int(stream["sample_rate"]) if stream.get("sample_rate") else None,
        channels=int(stream["channels"]) if stream.get("channels") else None,
    )


def split_audio_to_pcm_wav_chunks(
    source_path: Path,
    output_dir: Path,
    *,
    chunk_seconds: int,
    sample_rate: int = 16000,
    channels: int = 1,
    timeout: int = 3600,
) -> list[Path]:
    """Split audio into ASR-friendly PCM WAV chunks."""

    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be greater than zero.")

    check_ffmpeg()
    output_dir.mkdir(parents=True, exist_ok=True)
    template = output_dir / f"{source_path.stem}.chunk_%03d.wav"

    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source_path),
                "-f",
                "segment",
                "-segment_time",
                str(chunk_seconds),
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                str(sample_rate),
                "-ac",
                str(channels),
                str(template),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            f"ffmpeg failed to split '{source_path.name}' into audio chunks: {detail or 'unknown error'}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"ffmpeg timed out while splitting '{source_path.name}' into chunks.") from exc

    chunks = sorted(output_dir.glob(f"{source_path.stem}.chunk_*.wav"))
    if not chunks:
        raise RuntimeError(f"No audio chunks were created for '{source_path.name}'.")
    return chunks
