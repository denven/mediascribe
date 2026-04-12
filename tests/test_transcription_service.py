from pathlib import Path

import pytest

from mediascribe.asr import ASR_PROVIDERS
from mediascribe.asr.config import AzureASRConfig, LocalASRConfig
from mediascribe.models import TranscribedSegment
from mediascribe.transcription_service import (
    build_provider_config,
    transcribe_audio_files,
    transcribe_audio_input,
)


class FakeProvider:
    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        return [
            TranscribedSegment(
                start=0.0,
                end=1.0,
                speaker="Speaker 1",
                text=f"hello from {audio_path.name}",
            )
        ]


def test_asr_provider_registry_exposes_builtins() -> None:
    assert set(ASR_PROVIDERS) >= {"local", "azure", "aliyun", "iflytek"}


def test_transcribe_audio_files_writes_transcripts(tmp_path: Path) -> None:
    audio_file = tmp_path / "meeting.wav"
    audio_file.write_bytes(b"wav-data")

    result = transcribe_audio_files(
        [audio_file],
        FakeProvider(),
        output_dir=tmp_path,
        speaker_names=["Alice"],
    )

    assert result.processed_files == [audio_file]
    assert len(result.transcript_paths) == 1
    assert result.transcript_paths[0].read_text(encoding="utf-8").find("Alice: hello from meeting.wav") != -1


def test_transcribe_audio_input_uses_scanner_and_provider(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    audio_file = tmp_path / "meeting.wav"
    audio_file.write_bytes(b"wav-data")
    captured: dict[str, object] = {}
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_ENDPOINT", raising=False)

    monkeypatch.setattr(
        "mediascribe.transcription_service.scan_input",
        lambda input_path: [audio_file],
    )

    def fake_create_provider(provider_name: str, *, config) -> FakeProvider:
        captured["provider_name"] = provider_name
        captured["config"] = config
        return FakeProvider()

    monkeypatch.setattr("mediascribe.transcription_service.create_provider", fake_create_provider)

    result = transcribe_audio_input(
        "meeting.wav",
        output_dir=tmp_path,
        asr_provider="azure",
        language="en-US",
    )

    assert len(result.transcript_paths) == 1
    assert result.transcript_paths[0].exists()
    assert captured["provider_name"] == "azure"
    assert captured["config"] == AzureASRConfig(
        key=None,
        region=None,
        endpoint=None,
        language="en-US",
    )


def test_build_provider_config_reads_local_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HF_TOKEN", "hf_test")

    config = build_provider_config("local", model_size="large-v3", language="zh")

    assert config == LocalASRConfig(
        model_size="large-v3",
        language="zh",
        hf_token="hf_test",
    )


def test_build_provider_config_trims_azure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_SPEECH_KEY", "  test-key  ")
    monkeypatch.setenv("AZURE_SPEECH_REGION", " westus2 ")
    monkeypatch.setenv("AZURE_SPEECH_ENDPOINT", "   ")

    config = build_provider_config("azure", language="en-US")

    assert config == AzureASRConfig(
        key="test-key",
        region="westus2",
        endpoint=None,
        language="en-US",
    )


def test_transcribe_audio_files_raises_when_everything_fails(tmp_path: Path) -> None:
    audio_file = tmp_path / "meeting.wav"
    audio_file.write_bytes(b"wav-data")

    class BrokenProvider:
        def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="No files were successfully processed"):
        transcribe_audio_files([audio_file], BrokenProvider(), output_dir=tmp_path)
