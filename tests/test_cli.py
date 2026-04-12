"""Tests for the CLI module."""

import os
import sys

import pytest

from mediascribe.cli import build_parser, load_environment, main
from mediascribe.summary.config import LitellmSummaryConfig


def test_build_parser_collects_repeated_speaker_names() -> None:
    parser = build_parser()

    args = parser.parse_args([
        "meeting.wav",
        "--speaker-name", "Alice",
        "--speaker-name", "Bob",
    ])

    assert args.speaker_names == ["Alice", "Bob"]


def test_load_environment_reads_dotenv_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)

    (tmp_path / ".env").write_text(
        "AZURE_SPEECH_KEY=test-key\nAZURE_SPEECH_REGION=westus2\n",
        encoding="utf-8",
    )

    load_environment()

    assert os.environ["AZURE_SPEECH_KEY"] == "test-key"
    assert os.environ["AZURE_SPEECH_REGION"] == "westus2"


def test_load_environment_keeps_existing_shell_values(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AZURE_SPEECH_KEY", "shell-key")

    (tmp_path / ".env").write_text("AZURE_SPEECH_KEY=file-key\n", encoding="utf-8")

    load_environment()

    assert os.environ["AZURE_SPEECH_KEY"] == "shell-key"


def test_load_environment_skips_blank_values(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AZURE_SPEECH_ENDPOINT", raising=False)

    (tmp_path / ".env").write_text("AZURE_SPEECH_ENDPOINT=\n", encoding="utf-8")

    load_environment()

    assert "AZURE_SPEECH_ENDPOINT" not in os.environ


def test_main_summary_only_skips_transcription(tmp_path, monkeypatch) -> None:
    transcript = tmp_path / "meeting.txt"
    transcript.write_text("hello", encoding="utf-8")

    summary_path = tmp_path / "summary.md"

    monkeypatch.setattr("mediascribe.cli.load_environment", lambda: None)
    monkeypatch.setattr("mediascribe.cli.setup_logging", lambda verbose: None)
    monkeypatch.setattr(
        "mediascribe.cli.build_summary_config",
        lambda model, api_base: LitellmSummaryConfig(
            llm_model="ollama/qwen2.5:3b",
            api_base="http://localhost:11434",
        ),
    )
    monkeypatch.setattr(
        "mediascribe.cli.summarize_audio_input",
        lambda input_path, output_dir=None, llm_model=None, llm_api_base=None: summary_path,
    )
    monkeypatch.setattr(
        "mediascribe.cli.transcribe_audio_input",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("transcription should be skipped")),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["audio-summarizer", str(transcript), "--summary-only"],
    )

    main()


def test_main_audio_mode_generates_summary_by_default(tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "meeting.wav"
    audio_path.write_bytes(b"wav")
    transcript_path = tmp_path / "transcripts" / "meeting.txt"
    summary_path = tmp_path / "summary.md"
    calls: dict[str, object] = {}

    class FakeTranscriptionResult:
        transcript_paths = [transcript_path]
        processed_files = [audio_path]

    monkeypatch.setattr("mediascribe.cli.load_environment", lambda: None)
    monkeypatch.setattr("mediascribe.cli.setup_logging", lambda verbose: None)
    monkeypatch.setattr(
        "mediascribe.cli.build_summary_config",
        lambda model, api_base: LitellmSummaryConfig(
            llm_model="ollama/qwen2.5:3b",
            api_base="http://localhost:11434",
        ),
    )
    monkeypatch.setattr(
        "mediascribe.cli.transcribe_audio_input",
        lambda *args, **kwargs: FakeTranscriptionResult(),
    )
    monkeypatch.setattr(
        "mediascribe.cli.generate_audio_summary",
        lambda transcript_paths, output_dir, llm_model=None, llm_api_base=None, source_references=None: (
            calls.setdefault("transcript_paths", transcript_paths),
            calls.setdefault("llm_model", llm_model),
            calls.setdefault("llm_api_base", llm_api_base),
            calls.setdefault("source_references", source_references),
            summary_path,
        )[-1],
    )

    main([str(audio_path)])

    assert calls["transcript_paths"] == [transcript_path]
    assert calls["llm_model"] == "ollama/qwen2.5:3b"
    assert calls["llm_api_base"] == "http://localhost:11434"
    assert calls["source_references"] == [str(audio_path.resolve())]


def test_main_transcript_only_skips_summary_resolution_and_generation(tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "meeting.wav"
    audio_path.write_bytes(b"wav")

    class FakeTranscriptionResult:
        transcript_paths = [tmp_path / "transcripts" / "meeting.txt"]
        processed_files = [audio_path]

    monkeypatch.setattr("mediascribe.cli.load_environment", lambda: None)
    monkeypatch.setattr("mediascribe.cli.setup_logging", lambda verbose: None)
    monkeypatch.setattr(
        "mediascribe.cli.build_summary_config",
        lambda model, api_base: (_ for _ in ()).throw(AssertionError("summary config should not be resolved")),
    )
    monkeypatch.setattr(
        "mediascribe.cli.generate_audio_summary",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("summary should be skipped")),
    )
    monkeypatch.setattr(
        "mediascribe.cli.transcribe_audio_input",
        lambda *args, **kwargs: FakeTranscriptionResult(),
    )

    main([str(audio_path), "--transcript-only"])


def test_main_no_summary_alias_skips_summary_resolution_and_generation(tmp_path, monkeypatch) -> None:
    audio_path = tmp_path / "meeting.wav"
    audio_path.write_bytes(b"wav")

    class FakeTranscriptionResult:
        transcript_paths = [tmp_path / "transcripts" / "meeting.txt"]
        processed_files = [audio_path]

    monkeypatch.setattr("mediascribe.cli.load_environment", lambda: None)
    monkeypatch.setattr("mediascribe.cli.setup_logging", lambda verbose: None)
    monkeypatch.setattr(
        "mediascribe.cli.build_summary_config",
        lambda model, api_base: (_ for _ in ()).throw(AssertionError("summary config should not be resolved")),
    )
    monkeypatch.setattr(
        "mediascribe.cli.generate_audio_summary",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("summary should be skipped")),
    )
    monkeypatch.setattr(
        "mediascribe.cli.transcribe_audio_input",
        lambda *args, **kwargs: FakeTranscriptionResult(),
    )

    main([str(audio_path), "--no-summary"])


def test_main_rejects_conflicting_summary_and_transcript_only_flags(monkeypatch) -> None:
    monkeypatch.setattr("mediascribe.cli.load_environment", lambda: None)
    monkeypatch.setattr("mediascribe.cli.setup_logging", lambda verbose: None)

    with pytest.raises(SystemExit, match="2"):
        main(["meeting.wav", "--summary-only", "--transcript-only"])


def test_main_dispatches_transcribe_subcommand(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(
        "mediascribe.cli.run_audio_transcriber",
        lambda argv: captured.setdefault("argv", argv),
    )

    main(["transcribe", "meeting.wav", "--asr", "azure"])

    assert captured["argv"] == ["meeting.wav", "--asr", "azure"]


def test_main_dispatches_summarize_subcommand(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(
        "mediascribe.cli.run_text_summarizer",
        lambda argv: captured.setdefault("argv", argv),
    )

    main(["summarize", "output"])

    assert captured["argv"] == ["--summary-title", "Summary", "output"]


def test_main_dispatches_video_subcommand(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(
        "mediascribe.cli.run_video_summarizer",
        lambda argv: captured.setdefault("argv", argv),
    )

    main(["video", "lesson.mp4", "--force-asr"])

    assert captured["argv"] == ["lesson.mp4", "--force-asr"]


def test_main_dispatches_doctor_video_auth_subcommand(monkeypatch) -> None:
    captured = {}

    monkeypatch.setattr(
        "mediascribe.cli.run_video_auth_doctor",
        lambda argv: captured.setdefault("argv", argv),
    )

    main(["doctor-video-auth", "https://example.com/video"])

    assert captured["argv"] == ["https://example.com/video"]
