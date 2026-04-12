"""Video summary entrypoint built on top of the existing audio/text pipelines."""

import argparse
import logging
import sys
from pathlib import Path

from mediascribe.audio_summary_service import summarize_audio_input
from mediascribe.config import DEFAULT_ASR_PROVIDER, DEFAULT_OUTPUT_DIR, DEFAULT_WHISPER_MODEL
from mediascribe.media_extract_service import extract_audio_for_video
from mediascribe.runtime import load_environment, setup_logging
from mediascribe.subtitle_fetch_service import fetch_best_subtitle
from mediascribe.summary.adapters import build_summary_config
from mediascribe.text_summary_service import summarize_text_input
from mediascribe.transcription_service import (
    ASR_PROVIDERS,
    transcribe_audio_input,
)
from mediascribe.video_input_service import resolve_video_input
from mediascribe.video_models import VideoInput, VideoSummaryResult
from mediascribe.yt_dlp_auth import resolve_yt_dlp_auth_options

logger = logging.getLogger(__name__)


def _video_source_reference(video_input: VideoInput) -> str:
    if video_input.kind == "local_file":
        return str(video_input.local_path.resolve())
    return video_input.url


def summarize_video_input(
    input_value: str,
    output_dir: Path,
    *,
    prefer: str = "subtitles",
    force_subtitles: bool = False,
    force_asr: bool = False,
    extract_audio_only: bool = False,
    subtitle_lang: str | None = None,
    asr_provider: str = DEFAULT_ASR_PROVIDER,
    model_size: str = DEFAULT_WHISPER_MODEL,
    language: str | None = None,
    speaker_names: list[str] | None = None,
    llm_model: str | None = None,
    llm_api_base: str | None = None,
    yt_dlp_cookies: str | None = None,
    yt_dlp_cookies_from_browser: str | None = None,
) -> VideoSummaryResult:
    """Summarize a local video file or remote video URL."""

    if force_subtitles and force_asr:
        raise ValueError("`--force-subtitles` and `--force-asr` cannot be used together.")
    if force_subtitles and extract_audio_only:
        raise ValueError("`--force-subtitles` and `--extract-audio-only` cannot be used together.")

    if speaker_names and not force_subtitles and not force_asr and prefer == "subtitles":
        logger.info(
            "Speaker names were provided, preferring the ASR path because subtitle processing cannot apply diarized speaker renaming."
        )
        prefer = "asr"

    video_input = resolve_video_input(input_value)
    subtitle_path = None
    yt_dlp_auth = resolve_yt_dlp_auth_options(
        cookies_file=yt_dlp_cookies,
        cookies_from_browser=yt_dlp_cookies_from_browser,
        target_url=video_input.url,
    )

    should_try_subtitles = not force_asr and not extract_audio_only
    should_prefer_subtitles = force_subtitles or prefer == "subtitles"

    if should_try_subtitles:
        subtitle_path = fetch_best_subtitle(
            video_input,
            output_dir,
            subtitle_lang=subtitle_lang,
            yt_dlp_auth=yt_dlp_auth,
        )
        if subtitle_path is not None and should_prefer_subtitles:
            summary_path = summarize_text_input(
                str(subtitle_path),
                output_dir=output_dir,
                llm_model=llm_model,
                llm_api_base=llm_api_base,
                summary_title="Video Summary",
                source_references=[_video_source_reference(video_input)],
            )
            return VideoSummaryResult(
                summary_path=summary_path,
                strategy_used="subtitles",
                subtitle_path=subtitle_path,
            )

    if force_subtitles:
        raise RuntimeError("No subtitles were available for this video input.")

    try:
        audio_path = extract_audio_for_video(video_input, output_dir, yt_dlp_auth=yt_dlp_auth)
        if extract_audio_only:
            return VideoSummaryResult(
                summary_path=None,
                strategy_used="audio_extract_only",
                subtitle_path=subtitle_path,
                audio_path=audio_path,
            )
        transcription_result = transcribe_audio_input(
            str(audio_path),
            output_dir=output_dir,
            asr_provider=asr_provider,
            model_size=model_size,
            language=language,
            speaker_names=speaker_names,
        )
        summary_path = summarize_audio_input(
            str(output_dir),
            output_dir=output_dir,
            llm_model=llm_model,
            llm_api_base=llm_api_base,
            summary_title="Video Summary",
            source_references=[_video_source_reference(video_input)],
        )
        return VideoSummaryResult(
            summary_path=summary_path,
            strategy_used="audio_asr",
            subtitle_path=subtitle_path,
            audio_path=audio_path,
            transcript_paths=transcription_result.transcript_paths,
        )
    except (EnvironmentError, RuntimeError, ValueError) as exc:
        if subtitle_path is not None and not force_asr:
            logger.warning("ASR path failed, falling back to subtitles: %s", exc)
            summary_path = summarize_text_input(
                str(subtitle_path),
                output_dir=output_dir,
                llm_model=llm_model,
                llm_api_base=llm_api_base,
                summary_title="Video Summary",
                source_references=[_video_source_reference(video_input)],
            )
            return VideoSummaryResult(
                summary_path=summary_path,
                strategy_used="subtitles_fallback",
                subtitle_path=subtitle_path,
            )
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mediascribe video",
        description="Summarize a local video file or remote video URL.",
    )
    parser.add_argument("input", help="Path to a local video file or a remote video URL.")
    parser.add_argument(
        "-o",
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--prefer",
        choices=("subtitles", "asr"),
        default="subtitles",
        help="Preferred processing path when both subtitles and ASR are available.",
    )
    parser.add_argument(
        "--force-subtitles",
        action="store_true",
        help="Require subtitles and fail if none are available.",
    )
    parser.add_argument(
        "--force-asr",
        action="store_true",
        help="Skip subtitles and force the audio transcription path.",
    )
    parser.add_argument(
        "--extract-audio-only",
        action="store_true",
        help="Extract or download ASR-ready audio and stop without generating transcripts or summary.",
    )
    parser.add_argument(
        "--subtitle-lang",
        default=None,
        help="Preferred subtitle language code when fetching remote subtitles.",
    )
    parser.add_argument(
        "--yt-dlp-cookies",
        default=None,
        help="Path to a Netscape cookies.txt file passed through to yt-dlp for remote video access.",
    )
    parser.add_argument(
        "--yt-dlp-cookies-from-browser",
        default=None,
        help=(
            "Browser cookie source passed through to yt-dlp, for example `edge`, `chrome`, "
            "or `edge:Default`."
        ),
    )
    parser.add_argument(
        "--asr",
        default=DEFAULT_ASR_PROVIDER,
        choices=sorted(ASR_PROVIDERS),
        help=f"ASR provider for the audio fallback path (default: {DEFAULT_ASR_PROVIDER}).",
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
        help="Audio language locale (BCP-47) for the ASR fallback path, e.g. 'zh-CN', 'en-US'.",
    )
    parser.add_argument(
        "--speaker-name",
        dest="speaker_names",
        action="append",
        default=[],
        help=(
            "Predefine speaker names for the video ASR path in diarization order. "
            "Repeat the flag for multiple names, for example: --speaker-name Alice --speaker-name Bob"
        ),
    )
    parser.add_argument(
        "--llm-model",
        default=None,
        help="LLM model in litellm format. Defaults to the local Ollama model if omitted.",
    )
    parser.add_argument(
        "--llm-api-base",
        default=None,
        help="Optional LiteLLM API base override, for example http://localhost:11434 for Ollama.",
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
        summary_config = None if args.extract_audio_only else build_summary_config(
            args.llm_model,
            args.llm_api_base,
        )
        result = summarize_video_input(
            args.input,
            output_dir=Path(args.output_dir),
            prefer=args.prefer,
            force_subtitles=args.force_subtitles,
            force_asr=args.force_asr,
            extract_audio_only=args.extract_audio_only,
            subtitle_lang=args.subtitle_lang,
            asr_provider=args.asr,
            model_size=args.model,
            language=args.language,
            speaker_names=args.speaker_names,
            llm_model=None if summary_config is None else summary_config.llm_model,
            llm_api_base=None if summary_config is None else summary_config.api_base,
            yt_dlp_cookies=args.yt_dlp_cookies,
            yt_dlp_cookies_from_browser=args.yt_dlp_cookies_from_browser,
        )
    except (EnvironmentError, FileNotFoundError, RuntimeError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    if result.summary_path is not None:
        logger.info("Video summary generated: %s", result.summary_path)
    if result.audio_path is not None and result.strategy_used == "audio_extract_only":
        logger.info("Audio extracted: %s", result.audio_path)
        logger.info("Next step: uv run mediascribe \"%s\" --asr %s", result.audio_path, args.asr)
    logger.info("Processing strategy: %s", result.strategy_used)


def main() -> None:
    run()
