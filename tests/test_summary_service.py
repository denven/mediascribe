from pathlib import Path

import pytest

from mediascribe.audio_summary_service import (
    infer_audio_summary_output_dir,
    scan_audio_summary_input,
    summarize_audio_input,
)


def test_scan_audio_summary_input_accepts_single_file(tmp_path: Path) -> None:
    transcript = tmp_path / "meeting.txt"
    transcript.write_text("hello", encoding="utf-8")

    assert scan_audio_summary_input(str(transcript)) == [transcript]


def test_scan_audio_summary_input_falls_back_to_transcripts_subdir(tmp_path: Path) -> None:
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    first = transcripts_dir / "a.txt"
    second = transcripts_dir / "b.md"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")

    assert scan_audio_summary_input(str(tmp_path)) == [first, second]


def test_infer_audio_summary_output_dir_uses_parent_of_transcripts_dir(tmp_path: Path) -> None:
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    transcript = transcripts_dir / "meeting.txt"
    transcript.write_text("hello", encoding="utf-8")

    assert infer_audio_summary_output_dir([transcript]) == tmp_path


def test_summarize_audio_input_calls_generate_summary(tmp_path: Path, monkeypatch) -> None:
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    transcript = transcripts_dir / "meeting.txt"
    transcript.write_text("hello", encoding="utf-8")

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

    def fake_write_summary_document(summary_result, output_dir, summary_title="Audio Summary", output_filename="summary.md"):
        captured["output_dir"] = output_dir
        captured["summary_title"] = summary_title
        return output_dir / output_filename

    monkeypatch.setattr("mediascribe.audio_summary_service.summarize_text_sources", fake_summarize_text_sources)
    monkeypatch.setattr("mediascribe.audio_summary_service.write_summary_document", fake_write_summary_document)

    result = summarize_audio_input(
        str(tmp_path),
        llm_model="ollama/qwen2.5:3b",
        llm_api_base="http://localhost:11434",
    )

    assert result == tmp_path / "summary.md"
    assert captured["source_names"] == ["meeting"]
    assert captured["source_references"] == [str(transcript.resolve())]
    assert captured["output_dir"] == tmp_path
    assert captured["llm_model"] == "ollama/qwen2.5:3b"
    assert captured["llm_api_base"] == "http://localhost:11434"
    assert captured["summary_title"] == "Audio Summary"


def test_scan_audio_summary_input_rejects_unsupported_file(tmp_path: Path) -> None:
    transcript = tmp_path / "meeting.json"
    transcript.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported transcript format"):
        scan_audio_summary_input(str(transcript))
