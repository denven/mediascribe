"""Reusable summary service for arbitrary text strings and text files."""

import argparse
import logging
import sys
from pathlib import Path

from mediascribe.config import SUPPORTED_TRANSCRIPT_EXTENSIONS
from mediascribe.runtime import load_environment, setup_logging
from mediascribe.summary.config import TextSource
from mediascribe.summary.service import (
    apply_source_references,
    load_text_sources_from_files,
    summarize_text_sources,
    write_summary_document,
)

logger = logging.getLogger(__name__)


def scan_text_input(
    input_path: str,
    supported_extensions: set[str] | None = None,
) -> list[Path]:
    """Return text file paths from a file or directory path."""
    extensions = supported_extensions or SUPPORTED_TRANSCRIPT_EXTENSIONS
    path = Path(input_path)

    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        _validate_text_extension(path, extensions)
        return [path]

    if path.is_dir():
        text_files = _scan_text_dir(path, extensions)
        if text_files:
            logger.info("Found %d text file(s) in %s", len(text_files), path)
            return text_files

        transcripts_dir = path / "transcripts"
        if transcripts_dir.is_dir():
            text_files = _scan_text_dir(transcripts_dir, extensions)
            if text_files:
                logger.info("Found %d text file(s) in %s", len(text_files), transcripts_dir)
                return text_files

        raise ValueError(
            f"No supported text files found in directory: {path}\n"
            f"Supported formats: {', '.join(sorted(extensions))}"
        )

    raise ValueError(f"Input path is neither a file nor a directory: {path}")


def summarize_text_input(
    input_path: str,
    output_dir: Path | None = None,
    llm_model: str | None = None,
    llm_api_base: str | None = None,
    summary_title: str = "Text Summary",
    supported_extensions: set[str] | None = None,
    source_references: list[str] | None = None,
) -> Path:
    """Generate a summary from existing text files."""
    text_paths = scan_text_input(input_path, supported_extensions=supported_extensions)
    text_sources = apply_source_references(
        load_text_sources_from_files(text_paths),
        source_references=source_references,
    )
    summary_result = summarize_text_sources(
        text_sources,
        llm_model=llm_model,
        llm_api_base=llm_api_base,
    )
    return write_summary_document(
        summary_result,
        output_dir or infer_summary_output_dir(text_paths),
        summary_title=summary_title,
    )


def summarize_raw_text_to_file(
    text: str,
    output_dir: Path,
    source_name: str = "input",
    llm_model: str | None = None,
    llm_api_base: str | None = None,
    summary_title: str = "Text Summary",
    source_reference: str | None = None,
) -> Path:
    """Generate a summary from raw text and write it to disk."""
    summary_result = summarize_text_sources(
        [TextSource(name=source_name, content=text, reference=source_reference)],
        llm_model=llm_model,
        llm_api_base=llm_api_base,
    )
    return write_summary_document(summary_result, output_dir, summary_title=summary_title)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mediascribe-text",
        description="Summarize raw text or existing text files with an LLM.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to a text file or directory of text files.",
    )
    parser.add_argument(
        "--text",
        default=None,
        help="Raw text to summarize directly.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=None,
        help="Directory where summary.md will be written. If omitted, infer it from the input path.",
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
        "--source-name",
        default="input",
        help="Logical source name to show in metadata when using --text.",
    )
    parser.add_argument(
        "--summary-title",
        default="Text Summary",
        help="Markdown title written into the generated summary file.",
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

    if bool(args.input) == bool(args.text):
        parser.error("Provide exactly one of a path input or `--text`.")

    load_environment()
    setup_logging(args.verbose)

    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        if args.text:
            summary_path = summarize_raw_text_to_file(
                args.text,
                output_dir or Path("."),
                source_name=args.source_name,
                llm_model=args.llm_model,
                llm_api_base=args.llm_api_base,
                summary_title=args.summary_title,
            )
        else:
            summary_path = summarize_text_input(
                args.input,
                output_dir=output_dir,
                llm_model=args.llm_model,
                llm_api_base=args.llm_api_base,
                summary_title=args.summary_title,
            )
    except (EnvironmentError, FileNotFoundError, RuntimeError, ValueError) as e:
        logger.error(str(e))
        sys.exit(1)

    logger.info("Summary generated: %s", summary_path)


def main() -> None:
    run()


def infer_summary_output_dir(text_paths: list[Path]) -> Path:
    """Infer a natural summary output directory from text file locations."""
    if not text_paths:
        raise ValueError("At least one text path is required.")

    parent = text_paths[0].parent
    if parent.name == "transcripts":
        return parent.parent
    return parent


def _validate_text_extension(path: Path, supported_extensions: set[str]) -> None:
    if path.suffix.lower() not in supported_extensions:
        raise ValueError(
            f"Unsupported text format: {path.suffix}\n"
            f"Supported formats: {', '.join(sorted(supported_extensions))}"
        )


def _scan_text_dir(path: Path, supported_extensions: set[str]) -> list[Path]:
    return sorted(
        file
        for file in path.iterdir()
        if file.is_file() and file.suffix.lower() in supported_extensions
    )


if __name__ == "__main__":
    main()
