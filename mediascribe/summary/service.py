"""Generic text summary services powered by provider-style summary backends."""

import logging
from datetime import datetime
from pathlib import Path

from mediascribe.config import SUMMARY_FILENAME
from mediascribe.summary import create_summary_provider, resolve_summary_runtime
from mediascribe.summary.config import SummaryResult, TextSource

logger = logging.getLogger(__name__)


def summarize_text_sources(
    text_sources: list[TextSource],
    llm_model: str | None = None,
    llm_api_base: str | None = None,
) -> SummaryResult:
    """Summarize one or more named text inputs and return the generated content."""

    runtime = resolve_summary_runtime(llm_model, llm_api_base)
    provider = create_summary_provider(runtime.provider_name, config=runtime.config)
    return provider.summarize(text_sources)


def summarize_text(
    text: str,
    source_name: str = "input",
    llm_model: str | None = None,
    llm_api_base: str | None = None,
) -> str:
    """Summarize raw text and return the generated summary content."""

    result = summarize_text_sources(
        [TextSource(name=source_name, content=text)],
        llm_model=llm_model,
        llm_api_base=llm_api_base,
    )
    return result.content


def load_text_sources_from_files(file_paths: list[Path]) -> list[TextSource]:
    """Read text files into named summary sources."""

    return [
        TextSource(
            name=file_path.stem,
            content=file_path.read_text(encoding="utf-8"),
            reference=str(file_path.resolve()),
        )
        for file_path in file_paths
    ]


def apply_source_references(
    text_sources: list[TextSource],
    source_references: list[str] | None = None,
) -> list[TextSource]:
    """Override source references while keeping names and content unchanged."""

    if source_references is None:
        return text_sources
    if len(source_references) != len(text_sources):
        raise ValueError("Source reference count must match the number of text sources.")

    return [
        TextSource(
            name=source.name,
            content=source.content,
            reference=reference,
        )
        for source, reference in zip(text_sources, source_references)
    ]


def write_summary_document(
    summary_result: SummaryResult,
    output_dir: Path,
    summary_title: str = "Audio Summary",
    output_filename: str = SUMMARY_FILENAME,
) -> Path:
    """Persist a summary result as a Markdown document and return its path."""

    reference_block = ""
    if summary_result.source_references:
        reference_lines = "\n".join(f"- {reference}" for reference in summary_result.source_references)
        reference_block = f"Source paths / URLs:\n{reference_lines}\n\n"

    header = (
        f"# {summary_title}\n\n"
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Model: {summary_result.llm_model}\n"
        f"Source files: {', '.join(summary_result.source_names)}\n"
        f"{reference_block}"
        f"---\n\n"
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_filename
    output_path.write_text(header + summary_result.content, encoding="utf-8")
    logger.info("Summary written: %s", output_path)

    return output_path


def generate_summary(
    transcript_paths: list[Path],
    output_dir: Path,
    llm_model: str | None = None,
    llm_api_base: str | None = None,
) -> Path:
    """Read transcript files and generate a single Markdown summary."""

    summary_result = summarize_text_sources(
        load_text_sources_from_files(transcript_paths),
        llm_model=llm_model,
        llm_api_base=llm_api_base,
    )
    return write_summary_document(summary_result, output_dir, summary_title="Audio Summary")
