from pathlib import Path
import tempfile

import pytest
import requests

from mediascribe.asr.config import AzureASRConfig
from mediascribe.asr.azure import AzureASRProvider


def test_build_definition_uses_supported_diarization_shape() -> None:
    provider = AzureASRProvider(
        AzureASRConfig(
            key="test-key",
            region="westus2",
        )
    )

    definition = provider._build_definition()

    assert "channels" not in definition
    assert definition["diarization"] == {"enabled": True, "maxSpeakers": 10}
    assert "zh-CN" in definition["locales"]


def test_build_definition_uses_explicit_language_only() -> None:
    provider = AzureASRProvider(
        AzureASRConfig(
            key="test-key",
            region="westus2",
            language="en-US",
        )
    )

    definition = provider._build_definition()

    assert definition["locales"] == ["en-US"]


def test_blank_custom_endpoint_falls_back_to_region_url() -> None:
    provider = AzureASRProvider(
        AzureASRConfig(
            key="test-key",
            region="westus2",
            endpoint="   ",
            language="en-US",
        )
    )

    assert provider._endpoint == "https://westus2.api.cognitive.microsoft.com"


def test_transcribe_surfaces_azure_error_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = AzureASRProvider(
        AzureASRConfig(
            key="test-key",
            region="westus2",
            language="en-US",
        )
    )

    response = requests.Response()
    response.status_code = 422
    response._content = b'{"error":{"code":"InvalidRequest","message":"Diarization does not support channels."}}'
    response.url = "https://example.test/transcriptions:transcribe"
    response.request = requests.Request("POST", response.url).prepare()

    def fake_post(*args, **kwargs):
        return response

    monkeypatch.setattr("mediascribe.asr.providers.cloud.azure.requests.post", fake_post)

    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = Path(tmp_dir) / "sample.wav"
        audio_path.write_bytes(b"wav-data")

        with pytest.raises(requests.HTTPError, match="Diarization does not support channels"):
            provider.transcribe(audio_path)


def test_transcribe_normalizes_non_wav_audio_before_upload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = AzureASRProvider(
        AzureASRConfig(
            key="test-key",
            region="westus2",
            language="en-US",
        )
    )
    captured: dict[str, object] = {}

    def fake_convert(source: Path, target: Path, **kwargs) -> Path:
        captured["source"] = source
        captured["target"] = target
        target.write_bytes(b"normalized-wav")
        return target

    def fake_post(url, headers, files, timeout):
        captured["audio_name"] = files["audio"][0]
        captured["audio_type"] = files["audio"][2]
        response = requests.Response()
        response.status_code = 200
        response._content = b'{"phrases":[]}'
        response.url = url
        response.request = requests.Request("POST", url).prepare()
        return response

    monkeypatch.setattr(
        "mediascribe.asr.providers.cloud.azure.convert_audio_to_pcm_wav",
        fake_convert,
    )
    monkeypatch.setattr("mediascribe.asr.providers.cloud.azure.requests.post", fake_post)

    audio_path = tmp_path / "sample.m4a"
    audio_path.write_bytes(b"m4a-data")

    result = provider.transcribe(audio_path)

    assert result == []
    assert captured["source"] == audio_path
    assert str(captured["target"]).endswith(".wav")
    assert str(captured["audio_name"]).endswith(".wav")
    assert captured["audio_type"] in {"audio/wav", "audio/x-wav"}


def test_transcribe_retries_wav_with_normalization_after_decode_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = AzureASRProvider(
        AzureASRConfig(
            key="test-key",
            region="westus2",
            language="en-US",
        )
    )
    call_count = {"post": 0, "convert": 0}

    def fake_convert(source: Path, target: Path, **kwargs) -> Path:
        call_count["convert"] += 1
        target.write_bytes(b"normalized-wav")
        return target

    def fake_post(url, headers, files, timeout):
        call_count["post"] += 1
        response = requests.Response()
        response.url = url
        response.request = requests.Request("POST", url).prepare()
        if call_count["post"] == 1:
            response.status_code = 422
            response._content = (
                b'{"error":{"code":"InvalidAudio","message":"The audio stream could not be decoded with the provided configuration."}}'
            )
            return response

        response.status_code = 200
        response._content = (
            b'{"phrases":[{"speaker":1,"offsetMilliseconds":0,"durationMilliseconds":800,"text":"hello"}]}'
        )
        return response

    monkeypatch.setattr(
        "mediascribe.asr.providers.cloud.azure.convert_audio_to_pcm_wav",
        fake_convert,
    )
    monkeypatch.setattr("mediascribe.asr.providers.cloud.azure.requests.post", fake_post)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"wav-data")

    result = provider.transcribe(audio_path)

    assert len(result) == 1
    assert result[0].text == "hello"
    assert call_count == {"post": 2, "convert": 1}


def test_transcribe_auto_splits_large_or_long_audio_for_azure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    provider = AzureASRProvider(
        AzureASRConfig(
            key="test-key",
            region="westus2",
            language="en-US",
        )
    )
    source_path = tmp_path / "sample.wav"
    source_path.write_bytes(b"source-wav")
    chunk1 = tmp_path / "sample.chunk_000.wav"
    chunk2 = tmp_path / "sample.chunk_001.wav"
    chunk1.write_bytes(b"chunk1")
    chunk2.write_bytes(b"chunk2")
    calls: list[str] = []

    def fake_inspect(path: Path):
        if path == source_path:
            return type("Info", (), {"size_bytes": 200 * 1024 * 1024, "duration_seconds": 4000.0})()
        if path == chunk1:
            return type("Info", (), {"size_bytes": 10, "duration_seconds": 1800.0})()
        if path == chunk2:
            return type("Info", (), {"size_bytes": 10, "duration_seconds": 1200.0})()
        raise AssertionError(f"Unexpected inspect path: {path}")

    def fake_split(path: Path, output_dir: Path, *, chunk_seconds: int, **kwargs):
        assert path == source_path
        assert chunk_seconds == 1800
        return [chunk1, chunk2]

    def fake_post(url, headers, files, timeout):
        calls.append(files["audio"][0])
        response = requests.Response()
        response.status_code = 200
        response.url = url
        response.request = requests.Request("POST", url).prepare()
        if len(calls) == 1:
            response._content = (
                b'{"phrases":[{"speaker":1,"offsetMilliseconds":0,"durationMilliseconds":500,"text":"first"}]}'
            )
        else:
            response._content = (
                b'{"phrases":[{"speaker":1,"offsetMilliseconds":0,"durationMilliseconds":500,"text":"second"}]}'
            )
        return response

    monkeypatch.setattr("mediascribe.asr.providers.cloud.azure.inspect_audio_media", fake_inspect)
    monkeypatch.setattr(
        "mediascribe.asr.providers.cloud.azure.split_audio_to_pcm_wav_chunks",
        fake_split,
    )
    monkeypatch.setattr("mediascribe.asr.providers.cloud.azure.requests.post", fake_post)

    result = provider.transcribe(source_path)

    assert calls == [chunk1.name, chunk2.name]
    assert [segment.text for segment in result] == ["first", "second"]
    assert result[1].start == pytest.approx(1800.0)


def test_missing_region_and_endpoint_is_rejected() -> None:
    with pytest.raises(EnvironmentError, match="endpoint configuration is required"):
        AzureASRProvider(AzureASRConfig(key="test-key"))
