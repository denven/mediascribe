"""Reusable transcription service for audio files and directories."""

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from mediascribe.asr import ASR_PROVIDERS, create_provider
from mediascribe.asr.adapters import resolve_provider_config
from mediascribe.asr.config import ASRConfig
from mediascribe.config import DEFAULT_ASR_PROVIDER, DEFAULT_OUTPUT_DIR, DEFAULT_WHISPER_MODEL
from mediascribe.ffmpeg_utils import check_ffmpeg
from mediascribe.formatter import apply_speaker_names, format_transcript, write_transcript
from mediascribe.runtime import load_environment, setup_logging
from mediascribe.scanner import scan_input

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptionResult:
    transcript_paths: list[Path]
    processed_files: list[Path]


def log_local_asr_resource_hint() -> None:
    """Warn when the local ASR path may be unexpectedly heavy on hardware."""

    logger.warning(
        "Local ASR (`--asr local`) uses much more CPU/GPU/RAM than cloud ASR.\n"
        "If you want lower local hardware usage, try a cloud provider such as "
        "`--asr azure`, `--asr aliyun`, or `--asr iflytek`."
    )


def transcribe_audio_input(
    input_path: str,
    output_dir: Path,
    asr_provider: str = DEFAULT_ASR_PROVIDER,
    model_size: str = DEFAULT_WHISPER_MODEL,
    language: str | None = None,
    speaker_names: list[str] | None = None,
) -> TranscriptionResult:
    """Transcribe an audio file or directory into transcript files."""
    if asr_provider == "local":
        check_ffmpeg()
        log_local_asr_resource_hint()

    audio_files = scan_input(input_path)
    provider_config = build_provider_config(
        asr_provider,
        model_size=model_size,
        language=language,
    )
    provider = create_provider(
        asr_provider,
        config=provider_config,
    )
    return transcribe_audio_files(
        audio_files,
        provider,
        output_dir=output_dir,
        speaker_names=speaker_names,
    )


def build_provider_config(
    asr_provider: str,
    model_size: str = DEFAULT_WHISPER_MODEL,
    language: str | None = None,
) -> ASRConfig:
    """Resolve runtime config for an ASR provider from the environment."""
    return resolve_provider_config(
        asr_provider,
        model_size=model_size,
        language=language,
    )


def transcribe_audio_files(
    audio_files: list[Path],
    provider,
    output_dir: Path,
    speaker_names: list[str] | None = None,
) -> TranscriptionResult:
    """Transcribe a list of audio files with a ready-to-use provider."""
    transcript_paths: list[Path] = []
    processed_files: list[Path] = []

    if speaker_names:
        logger.info("Predefined speaker names: %s", ", ".join(speaker_names))

    for audio_path in audio_files:
        try:
            logger.info("Processing: %s", audio_path.name)

            segments = provider.transcribe(audio_path)
            segments = apply_speaker_names(segments, speaker_names)

            transcript_text = format_transcript(segments, audio_path.name)
            transcript_path = write_transcript(transcript_text, audio_path.name, output_dir)
            transcript_paths.append(transcript_path)
            processed_files.append(audio_path)
        except Exception as e:
            logger.error("Failed to process %s: %s", audio_path.name, e)
            continue

    if not transcript_paths:
        raise RuntimeError("No files were successfully processed.")

    logger.info("Transcription complete: %d file(s) processed.", len(transcript_paths))
    return TranscriptionResult(
        transcript_paths=transcript_paths,
        processed_files=processed_files,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mediascribe-transcriber",
        description="Transcribe audio files into transcript files without running summary generation.",
    )
    parser.add_argument(
        "input",
        help="Path to an audio file or a directory containing audio files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--asr",
        default=DEFAULT_ASR_PROVIDER,
        choices=sorted(ASR_PROVIDERS),
        help=f"ASR provider (default: {DEFAULT_ASR_PROVIDER}).",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_WHISPER_MODEL,
        help=f"Whisper model size, only for --asr local (default: {DEFAULT_WHISPER_MODEL}).",
    )
    parser.add_argument(
        "-l",
        "--language",
        default=None,
        help="Audio language code, e.g. 'zh', 'en'. Auto-detect if omitted.",
    )
    parser.add_argument(
        "--speaker-name",
        dest="speaker_names",
        action="append",
        default=[],
        help=(
            "Predefine speaker names in diarization order. Repeat the flag for multiple names, "
            "for example: --speaker-name Alice --speaker-name Bob"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def run(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    load_environment()
    setup_logging(args.verbose)

    try:
        result = transcribe_audio_input(
            args.input,
            output_dir=Path(args.output_dir),
            asr_provider=args.asr,
            model_size=args.model,
            language=args.language,
            speaker_names=args.speaker_names,
        )
    except (EnvironmentError, FileNotFoundError, RuntimeError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info("Transcript files written: %d", len(result.transcript_paths))


def main() -> None:
    run()


if __name__ == "__main__":
    main()
