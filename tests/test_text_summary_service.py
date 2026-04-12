from pathlib import Path

import pytest

from mediascribe.text_summary_service import (
    infer_summary_output_dir,
    scan_text_input,
    summarize_raw_text_to_file,
    summarize_text_input,
)


def test_scan_text_input_accepts_directory(tmp_path: Path) -> None:
    first = tmp_path / "a.txt"
    second = tmp_path / "b.md"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")

    assert scan_text_input(str(tmp_path)) == [first, second]


def test_scan_text_input_falls_back_to_transcripts_subdir(tmp_path: Path) -> None:
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    transcript = transcripts_dir / "meeting.txt"
    transcript.write_text("hello", encoding="utf-8")

    assert scan_text_input(str(tmp_path)) == [transcript]


def test_infer_summary_output_dir_uses_parent_of_transcripts_dir(tmp_path: Path) -> None:
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    transcript = transcripts_dir / "meeting.txt"
    transcript.write_text("hello", encoding="utf-8")

    assert infer_summary_output_dir([transcript]) == tmp_path


def test_summarize_text_input_calls_generic_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    text_file = tmp_path / "notes.txt"
    text_file.write_text("hello", encoding="utf-8")
    captured = {}

    def fake_summarize_text_sources(text_sources, llm_model=None, llm_api_base=None):
        captured["source_names"] = [source.name for source in text_sources]
        captured["source_references"] = [source.reference for source in text_sources]
        captured["llm_model"] = llm_model
        captured["llm_api_base"] = llm_api_base
        return type(
            "SummaryResult",
            (),
            {
                "content": "summary",
                "llm_model": llm_model,
                "source_names": captured["source_names"],
                "source_references": captured["source_references"],
            },
        )()

    def fake_write_summary_document(summary_result, output_dir, summary_title="Text Summary", output_filename="summary.md"):
        captured["output_dir"] = output_dir
        captured["summary_title"] = summary_title
        return output_dir / output_filename

    monkeypatch.setattr("mediascribe.text_summary_service.summarize_text_sources", fake_summarize_text_sources)
    monkeypatch.setattr("mediascribe.text_summary_service.write_summary_document", fake_write_summary_document)

    result = summarize_text_input(
        str(text_file),
        llm_model="ollama/qwen2.5:3b",
        llm_api_base="http://localhost:11434",
    )

    assert result == tmp_path / "summary.md"
    assert captured["source_names"] == ["notes"]
    assert captured["source_references"] == [str(text_file.resolve())]
    assert captured["llm_model"] == "ollama/qwen2.5:3b"
    assert captured["llm_api_base"] == "http://localhost:11434"
    assert captured["summary_title"] == "Text Summary"


def test_summarize_raw_text_to_file_calls_generic_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_summarize_text_sources(text_sources, llm_model=None, llm_api_base=None):
        captured["source_names"] = [source.name for source in text_sources]
        captured["content"] = [source.content for source in text_sources]
        captured["source_references"] = [source.reference for source in text_sources]
        captured["llm_model"] = llm_model
        captured["llm_api_base"] = llm_api_base
        return type(
            "SummaryResult",
            (),
            {
                "content": "summary",
                "llm_model": llm_model,
                "source_names": captured["source_names"],
                "source_references": captured["source_references"],
            },
        )()

    def fake_write_summary_document(summary_result, output_dir, summary_title="Text Summary", output_filename="summary.md"):
        captured["output_dir"] = output_dir
        captured["summary_title"] = summary_title
        return output_dir / output_filename

    monkeypatch.setattr("mediascribe.text_summary_service.summarize_text_sources", fake_summarize_text_sources)
    monkeypatch.setattr("mediascribe.text_summary_service.write_summary_document", fake_write_summary_document)

    result = summarize_raw_text_to_file(
        "hello world",
        tmp_path,
        source_name="manual",
        llm_model="ollama/qwen2.5:3b",
        llm_api_base="http://localhost:11434",
    )

    assert result == tmp_path / "summary.md"
    assert captured["source_names"] == ["manual"]
    assert captured["content"] == ["hello world"]
    assert captured["source_references"] == [None]
    assert captured["llm_model"] == "ollama/qwen2.5:3b"
    assert captured["llm_api_base"] == "http://localhost:11434"
