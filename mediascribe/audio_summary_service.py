"""Audio-transcript summary helpers built on the generic text summary services."""

import logging
from pathlib import Path

from mediascribe.config import SUPPORTED_TRANSCRIPT_EXTENSIONS
from mediascribe.summary.adapters import (
    build_summary_config,
    required_api_key_for_model,
    resolve_summary_api_base,
    resolve_summary_model,
)
from mediascribe.summary.config import SummaryResult, TextSource
from mediascribe.summary.providers.litellm_provider import litellm
from mediascribe.summary.service import (
    apply_source_references,
    load_text_sources_from_files,
    summarize_text_sources,
    write_summary_document,
)

logger = logging.getLogger(__name__)


def scan_audio_summary_input(input_path: str) -> list[Path]:
    """Return transcript file paths from a file or directory path.

    Accepts a single transcript file, a directory containing transcript files,
    or an output directory containing a `transcripts/` subdirectory.
    """
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        _validate_transcript_extension(path)
        return [path]

    if path.is_dir():
        transcript_files = _scan_transcript_dir(path)
        if transcript_files:
            logger.info("Found %d transcript file(s) in %s", len(transcript_files), path)
            return transcript_files

        transcripts_dir = path / "transcripts"
        if transcripts_dir.is_dir():
            transcript_files = _scan_transcript_dir(transcripts_dir)
            if transcript_files:
                logger.info(
                    "Found %d transcript file(s) in %s",
                    len(transcript_files),
                    transcripts_dir,
                )
                return transcript_files

        raise ValueError(
            f"No supported transcript files found in directory: {path}\n"
            f"Supported formats: {', '.join(sorted(SUPPORTED_TRANSCRIPT_EXTENSIONS))}"
        )

    raise ValueError(f"Input path is neither a file nor a directory: {path}")


def summarize_audio_input(
    input_path: str,
    output_dir: Path | None = None,
    llm_model: str | None = None,
    llm_api_base: str | None = None,
    summary_title: str = "Audio Summary",
    source_references: list[str] | None = None,
) -> Path:
    """Generate a summary from existing transcript files without rerunning ASR."""
    transcript_paths = scan_audio_summary_input(input_path)
    target_output_dir = output_dir or infer_audio_summary_output_dir(transcript_paths)
    return generate_audio_summary(
        transcript_paths,
        target_output_dir,
        llm_model=llm_model,
        llm_api_base=llm_api_base,
        summary_title=summary_title,
        source_references=source_references,
    )


def generate_audio_summary(
    transcript_paths: list[Path],
    output_dir: Path,
    llm_model: str | None = None,
    llm_api_base: str | None = None,
    summary_title: str = "Audio Summary",
    source_references: list[str] | None = None,
) -> Path:
    """Read transcript files and generate a single Markdown summary."""
    text_sources = apply_source_references(
        load_text_sources_from_files(transcript_paths),
        source_references=source_references,
    )
    summary_result = summarize_text_sources(
        text_sources,
        llm_model=llm_model,
        llm_api_base=llm_api_base,
    )
    return write_summary_document(summary_result, output_dir, summary_title=summary_title)


def summarize_text(
    text: str,
    source_name: str = "input",
    llm_model: str | None = None,
    llm_api_base: str | None = None,
) -> str:
    """Summarize raw text using the same runtime wiring as audio summary flows."""
    result = summarize_text_sources(
        [TextSource(name=source_name, content=text)],
        llm_model=llm_model,
        llm_api_base=llm_api_base,
    )
    return result.content


def infer_audio_summary_output_dir(transcript_paths: list[Path]) -> Path:
    """Infer a natural summary output directory from transcript file locations."""
    if not transcript_paths:
        raise ValueError("At least one transcript path is required.")

    parent = transcript_paths[0].parent
    if parent.name == "transcripts":
        return parent.parent
    return parent


def _scan_transcript_dir(path: Path) -> list[Path]:
    return sorted(
        file
        for file in path.iterdir()
        if file.is_file() and file.suffix.lower() in SUPPORTED_TRANSCRIPT_EXTENSIONS
    )


def _validate_transcript_extension(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_TRANSCRIPT_EXTENSIONS:
        raise ValueError(
            f"Unsupported transcript format: {path.suffix}\n"
            f"Supported formats: {', '.join(sorted(SUPPORTED_TRANSCRIPT_EXTENSIONS))}"
        )


__all__ = [
    "SummaryResult",
    "TextSource",
    "build_summary_config",
    "generate_audio_summary",
    "infer_audio_summary_output_dir",
    "litellm",
    "load_text_sources_from_files",
    "required_api_key_for_model",
    "resolve_summary_api_base",
    "resolve_summary_model",
    "scan_audio_summary_input",
    "summarize_audio_input",
    "summarize_text",
    "summarize_text_sources",
    "write_summary_document",
]
