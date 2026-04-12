"""CLI entry point: argument parsing and orchestration."""

import argparse
import logging
import sys
from pathlib import Path

from mediascribe.config import (
    DEFAULT_ASR_PROVIDER,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_WHISPER_MODEL,
)
from mediascribe.audio_summary_service import (
    build_summary_config,
    generate_audio_summary,
    summarize_audio_input,
)
from mediascribe.runtime import load_environment, setup_logging
from mediascribe.text_summary_service import run as run_text_summarizer
from mediascribe.transcription_service import (
    ASR_PROVIDERS,
    run as run_audio_transcriber,
    transcribe_audio_input,
)
from mediascribe.video_auth_doctor import run as run_video_auth_doctor
from mediascribe.video_summary_service import run as run_video_summarizer

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mediascribe",
        description="Transcribe audio files with speaker diarization and generate an LLM summary by default.",
    )
    parser.add_argument(
        "input",
        help="Path to an audio file/directory, or a transcript file/directory when using --summary-only.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help=(
            "Output directory. Defaults to ./output for transcription, "
            "or is inferred from the transcript location in --summary-only mode."
        ),
    )
    parser.add_argument(
        "--asr",
        default=DEFAULT_ASR_PROVIDER,
        choices=sorted(ASR_PROVIDERS),
        help=f"ASR provider (default: {DEFAULT_ASR_PROVIDER}).",
    )
    parser.add_argument(
        "-s", "--summarize",
        action="store_true",
        help="Generate an LLM-powered summary after transcription. Audio mode summarizes by default unless --transcript-only is used.",
    )
    parser.add_argument(
        "-m", "--model",
        default=DEFAULT_WHISPER_MODEL,
        help=f"Whisper model size, only for --asr local (default: {DEFAULT_WHISPER_MODEL}).",
    )
    parser.add_argument(
        "-l", "--language",
        default=None,
        help="Audio language locale (BCP-47), e.g. 'zh-CN', 'en-US'. Auto-detect if omitted.",
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
        "--llm-model",
        default=None,
        help="LLM model for summary in litellm format. Defaults to the local Ollama model if omitted.",
    )
    parser.add_argument(
        "--llm-api-base",
        default=None,
        help="Optional LiteLLM API base override, for example http://localhost:11434 for Ollama.",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Skip transcription and generate a summary directly from existing transcript files.",
    )
    parser.add_argument(
        "--transcript-only",
        "--no-summary",
        dest="transcript_only",
        action="store_true",
        help="Skip summary generation and only write transcript files. `--no-summary` is an alias.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv:
        if argv[0] == "transcribe":
            run_audio_transcriber(argv[1:])
            return
        if argv[0] == "summarize":
            run_text_summarizer(["--summary-title", "Summary", *argv[1:]])
            return
        if argv[0] == "video":
            run_video_summarizer(argv[1:])
            return
        if argv[0] == "doctor-video-auth":
            run_video_auth_doctor(argv[1:])
            return

    parser = build_parser()
    args = parser.parse_args(argv)

    load_environment()
    setup_logging(args.verbose)

    if args.summary_only and args.transcript_only:
        parser.error("--summary-only and --transcript-only cannot be used together.")

    if args.summary_only and args.speaker_names:
        logger.warning("--speaker-name is ignored when --summary-only is used.")

    summary_requested = args.summary_only or not args.transcript_only
    summary_config = None

    if summary_requested:
        try:
            summary_config = build_summary_config(args.llm_model, args.llm_api_base)
        except EnvironmentError as e:
            message = str(e)
            if not args.summary_only and not args.summarize and not args.transcript_only:
                message += "\nIf you only want transcripts, rerun with --transcript-only (or --no-summary)."
            logger.error(message)
            sys.exit(1)

    if args.summary_only:
        try:
            summary_path = summarize_audio_input(
                args.input,
                output_dir=Path(args.output_dir) if args.output_dir else None,
                llm_model=summary_config.llm_model,
                llm_api_base=summary_config.api_base,
            )
            logger.info("Summary generated: %s", summary_path)
            return
        except (FileNotFoundError, ValueError, RuntimeError) as e:
            logger.error(str(e))
            sys.exit(1)

    output_dir = Path(args.output_dir or DEFAULT_OUTPUT_DIR)

    logger.info("Using ASR provider: %s", args.asr)
    if summary_config is not None:
        logger.info("Using summary model: %s", summary_config.llm_model)

    try:
        transcription_result = transcribe_audio_input(
            args.input,
            output_dir=output_dir,
            asr_provider=args.asr,
            model_size=args.model,
            language=args.language,
            speaker_names=args.speaker_names,
        )
    except (EnvironmentError, FileNotFoundError, RuntimeError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    if not args.transcript_only:
        try:
            summary_path = generate_audio_summary(
                transcription_result.transcript_paths,
                output_dir,
                llm_model=summary_config.llm_model,
                llm_api_base=summary_config.api_base,
                source_references=[str(path.resolve()) for path in transcription_result.processed_files],
            )
            logger.info("Summary generated: %s", summary_path)
        except RuntimeError as e:
            logger.error("Summary generation failed: %s", e)
            logger.info("Transcripts are still available in %s", output_dir)
            sys.exit(1)
