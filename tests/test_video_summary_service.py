from pathlib import Path

import pytest

from mediascribe.summary.config import LitellmSummaryConfig
from mediascribe.video_models import VideoInput
from mediascribe.video_summary_service import build_parser, run, summarize_video_input


def test_summarize_video_input_prefers_subtitles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    subtitle_file = tmp_path / "output" / "subtitles" / "lesson.subtitle.txt"
    subtitle_file.parent.mkdir(parents=True)
    subtitle_file.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda video_input, output_dir, subtitle_lang=None, yt_dlp_auth=None: subtitle_file,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_text_input",
        lambda *args, **kwargs: tmp_path / "output" / "summary.md",
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.extract_audio_for_video",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("audio path should not run")),
    )

    result = summarize_video_input("lesson.mp4", tmp_path / "output")

    assert result.strategy_used == "subtitles"
    assert result.subtitle_path == subtitle_file


def test_summarize_video_input_falls_back_to_asr(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio_file = tmp_path / "output" / "media" / "lesson.wav"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"wav")
    transcript_path = tmp_path / "output" / "transcripts" / "lesson.txt"
    transcript_path.parent.mkdir(parents=True)
    transcript_path.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.extract_audio_for_video",
        lambda *args, **kwargs: audio_file,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.transcribe_audio_input",
        lambda *args, **kwargs: type("Result", (), {"transcript_paths": [transcript_path]})(),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_audio_input",
        lambda *args, **kwargs: tmp_path / "output" / "summary.md",
    )

    result = summarize_video_input("lesson.mp4", tmp_path / "output", llm_model="gpt-5.4-mini")

    assert result.strategy_used == "audio_asr"
    assert result.audio_path == audio_file
    assert result.transcript_paths == [transcript_path]


def test_summarize_video_input_falls_back_to_subtitles_if_preferred_asr_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    subtitle_file = tmp_path / "output" / "subtitles" / "lesson.subtitle.txt"
    subtitle_file.parent.mkdir(parents=True)
    subtitle_file.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: subtitle_file,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.extract_audio_for_video",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_text_input",
        lambda *args, **kwargs: tmp_path / "output" / "summary.md",
    )

    result = summarize_video_input("lesson.mp4", tmp_path / "output", prefer="asr")

    assert result.strategy_used == "subtitles_fallback"


def test_summarize_video_input_force_subtitles_requires_subtitle_source(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(RuntimeError, match="No subtitles were available"):
        summarize_video_input("lesson.mp4", tmp_path / "output", force_subtitles=True)


def test_build_parser_collects_ytdlp_cookie_options() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "https://example.com/video",
            "--yt-dlp-cookies",
            "cookies.txt",
            "--yt-dlp-cookies-from-browser",
            "edge",
        ]
    )

    assert args.yt_dlp_cookies == "cookies.txt"
    assert args.yt_dlp_cookies_from_browser == "edge"


def test_build_parser_collects_llm_api_base() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "lesson.mp4",
            "--llm-model",
            "ollama/qwen2.5:3b",
            "--llm-api-base",
            "http://localhost:11434",
        ]
    )

    assert args.llm_model == "ollama/qwen2.5:3b"
    assert args.llm_api_base == "http://localhost:11434"


def test_build_parser_collects_extract_audio_only_and_speaker_names() -> None:
    parser = build_parser()

    args = parser.parse_args(
        [
            "lesson.mp4",
            "--extract-audio-only",
            "--speaker-name",
            "Alice",
            "--speaker-name",
            "Bob",
        ]
    )

    assert args.extract_audio_only is True
    assert args.speaker_names == ["Alice", "Bob"]


def test_summarize_video_input_passes_original_url_as_source_reference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    subtitle_file = tmp_path / "output" / "subtitles" / "watch.subtitle.txt"
    subtitle_file.parent.mkdir(parents=True)
    subtitle_file.write_text("hello", encoding="utf-8")
    captured = {}

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="remote_url", source_name="watch", url=value),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: subtitle_file,
    )

    def fake_summarize_text_input(*args, **kwargs):
        captured["source_references"] = kwargs["source_references"]
        return tmp_path / "output" / "summary.md"

    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_text_input",
        fake_summarize_text_input,
    )

    summarize_video_input("https://example.com/video", tmp_path / "output")

    assert captured["source_references"] == ["https://example.com/video"]


def test_summarize_video_input_extract_audio_only_skips_transcription_and_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_file = tmp_path / "output" / "media" / "lesson.wav"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"wav")

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.extract_audio_for_video",
        lambda *args, **kwargs: audio_file,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.transcribe_audio_input",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("transcription should be skipped")),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_audio_input",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("summary should be skipped")),
    )

    result = summarize_video_input("lesson.mp4", tmp_path / "output", extract_audio_only=True)

    assert result.strategy_used == "audio_extract_only"
    assert result.audio_path == audio_file
    assert result.summary_path is None


def test_summarize_video_input_extract_audio_only_skips_subtitle_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_file = tmp_path / "output" / "media" / "lesson.wav"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"wav")

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subtitle path should be skipped")),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.extract_audio_for_video",
        lambda *args, **kwargs: audio_file,
    )

    result = summarize_video_input("lesson.mp4", tmp_path / "output", extract_audio_only=True)

    assert result.strategy_used == "audio_extract_only"


def test_summarize_video_input_passes_speaker_names_to_asr_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_file = tmp_path / "output" / "media" / "lesson.wav"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"wav")
    transcript_path = tmp_path / "output" / "transcripts" / "lesson.txt"
    transcript_path.parent.mkdir(parents=True)
    transcript_path.write_text("hello", encoding="utf-8")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.extract_audio_for_video",
        lambda *args, **kwargs: audio_file,
    )

    def fake_transcribe_audio_input(*args, **kwargs):
        captured["speaker_names"] = kwargs["speaker_names"]
        return type("Result", (), {"transcript_paths": [transcript_path]})()

    monkeypatch.setattr(
        "mediascribe.video_summary_service.transcribe_audio_input",
        fake_transcribe_audio_input,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_audio_input",
        lambda *args, **kwargs: tmp_path / "output" / "summary.md",
    )

    summarize_video_input(
        "lesson.mp4",
        tmp_path / "output",
        speaker_names=["Alice", "Bob"],
    )

    assert captured["speaker_names"] == ["Alice", "Bob"]


def test_summarize_video_input_speaker_names_prefer_asr_over_subtitles(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    subtitle_file = tmp_path / "output" / "subtitles" / "lesson.subtitle.txt"
    subtitle_file.parent.mkdir(parents=True)
    subtitle_file.write_text("hello", encoding="utf-8")
    audio_file = tmp_path / "output" / "media" / "lesson.wav"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"wav")
    transcript_path = tmp_path / "output" / "transcripts" / "lesson.txt"
    transcript_path.parent.mkdir(parents=True)
    transcript_path.write_text("hello", encoding="utf-8")

    monkeypatch.setattr(
        "mediascribe.video_summary_service.resolve_video_input",
        lambda value: VideoInput(raw_input=value, kind="local_file", source_name="lesson", local_path=Path(value)),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.fetch_best_subtitle",
        lambda *args, **kwargs: subtitle_file,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.extract_audio_for_video",
        lambda *args, **kwargs: audio_file,
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.transcribe_audio_input",
        lambda *args, **kwargs: type("Result", (), {"transcript_paths": [transcript_path]})(),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_audio_input",
        lambda *args, **kwargs: tmp_path / "output" / "summary.md",
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_text_input",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("subtitle summary should not run")),
    )

    result = summarize_video_input(
        "lesson.mp4",
        tmp_path / "output",
        speaker_names=["Alice"],
    )

    assert result.strategy_used == "audio_asr"


def test_run_extract_audio_only_skips_summary_model_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_file = tmp_path / "output" / "media" / "lesson.wav"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"wav")

    monkeypatch.setattr("mediascribe.video_summary_service.load_environment", lambda: None)
    monkeypatch.setattr("mediascribe.video_summary_service.setup_logging", lambda verbose: None)
    monkeypatch.setattr(
        "mediascribe.video_summary_service.build_summary_config",
        lambda model, api_base: (_ for _ in ()).throw(AssertionError("summary config should not be resolved")),
    )
    monkeypatch.setattr(
        "mediascribe.video_summary_service.summarize_video_input",
        lambda *args, **kwargs: type(
            "Result",
            (),
            {"summary_path": None, "strategy_used": "audio_extract_only", "audio_path": audio_file},
        )(),
    )

    run(["lesson.mp4", "--extract-audio-only", "-o", str(tmp_path / "output")])


def test_run_passes_llm_api_base_into_video_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr("mediascribe.video_summary_service.load_environment", lambda: None)
    monkeypatch.setattr("mediascribe.video_summary_service.setup_logging", lambda verbose: None)
    monkeypatch.setattr(
        "mediascribe.video_summary_service.build_summary_config",
        lambda model, api_base: LitellmSummaryConfig(
            llm_model="ollama/qwen2.5:3b",
            api_base="http://localhost:11434",
        ),
    )

    def fake_summarize_video_input(*args, **kwargs):
        captured["llm_model"] = kwargs["llm_model"]
        captured["llm_api_base"] = kwargs["llm_api_base"]
        return type(
            "Result",
            (),
            {"summary_path": tmp_path / "output" / "summary.md", "strategy_used": "subtitles", "audio_path": None},
        )()

    monkeypatch.setattr("mediascribe.video_summary_service.summarize_video_input", fake_summarize_video_input)

    run(["lesson.mp4", "--llm-api-base", "http://localhost:11434", "-o", str(tmp_path / "output")])

    assert captured["llm_model"] == "ollama/qwen2.5:3b"
    assert captured["llm_api_base"] == "http://localhost:11434"
