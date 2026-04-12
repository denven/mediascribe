import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def _load_module(module_name: str, relative_path: str):
    path = Path(relative_path)
    spec = spec_from_file_location(module_name, path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_openai_responses_example_extracts_direct_output_text() -> None:
    module = _load_module(
        "example_openai_responses_summary_provider",
        "examples/custom_providers/openai_responses_summary_provider.py",
    )

    assert module._extract_output_text({"output_text": "  hello world  "}) == "hello world"


def test_openai_responses_example_extracts_message_output_text() -> None:
    module = _load_module(
        "example_openai_responses_summary_provider_nested",
        "examples/custom_providers/openai_responses_summary_provider.py",
    )

    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": "first"},
                    {"type": "output_text", "text": "second"},
                ],
            }
        ]
    }

    assert module._extract_output_text(payload) == "first\nsecond"


def test_http_webhook_example_reads_nested_segment_path() -> None:
    module = _load_module(
        "example_http_webhook_asr_provider",
        "examples/custom_providers/http_webhook_asr_provider.py",
    )

    payload = {"data": {"segments": [{"start": 0.0, "end": 1.0, "speaker": "S1", "text": "hello"}]}}
    assert module._get_by_dotted_path(payload, "data.segments") == payload["data"]["segments"]


def test_http_webhook_example_normalizes_custom_field_names(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module(
        "example_http_webhook_asr_provider_custom_fields",
        "examples/custom_providers/http_webhook_asr_provider.py",
    )

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {
                "result": {
                    "items": [
                        {"begin": 1.5, "finish": 3.0, "who": "Speaker X", "utterance": "hello world"}
                    ]
                }
            }

    captured = {}

    def fake_post(url, headers, data, files, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["data"] = data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(module.requests, "post", fake_post)

    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"wav-data")

    provider = module.HttpWebhookASRProvider(
        module.HttpWebhookASRConfig(
            endpoint="https://example.test/webhook",
            api_key="abc",
            language="en-US",
            timeout_sec=42,
            response_path="result.items",
            text_field="utterance",
            speaker_field="who",
            start_field="begin",
            end_field="finish",
        )
    )

    segments = provider.transcribe(audio_path)

    assert captured["url"] == "https://example.test/webhook"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["data"]["language"] == "en-US"
    assert captured["timeout"] == 42
    assert len(segments) == 1
    assert segments[0].speaker == "Speaker X"
    assert segments[0].text == "hello world"
    assert segments[0].start == 1.5
    assert segments[0].end == 3.0


def test_http_webhook_example_resolver_reads_custom_mapping_env() -> None:
    module = _load_module(
        "example_http_webhook_asr_provider_resolver",
        "examples/custom_providers/http_webhook_asr_provider.py",
    )

    config = module.resolve_http_webhook_asr_config(
        language="fr",
        env={
            "WEBHOOK_ASR_URL": " https://example.test/asr ",
            "WEBHOOK_ASR_KEY": " secret ",
            "WEBHOOK_ASR_TIMEOUT": "15",
            "WEBHOOK_ASR_RESPONSE_PATH": "data.items",
            "WEBHOOK_ASR_TEXT_FIELD": "utterance",
            "WEBHOOK_ASR_SPEAKER_FIELD": "speaker_name",
            "WEBHOOK_ASR_START_FIELD": "begin",
            "WEBHOOK_ASR_END_FIELD": "finish",
        },
    )

    assert config.endpoint == "https://example.test/asr"
    assert config.api_key == "secret"
    assert config.language == "fr"
    assert config.timeout_sec == 15
    assert config.response_path == "data.items"
    assert config.text_field == "utterance"
    assert config.speaker_field == "speaker_name"
    assert config.start_field == "begin"
    assert config.end_field == "finish"
