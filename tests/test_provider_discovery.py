import sys
from pathlib import Path

from mediascribe.asr import create_provider
from mediascribe.asr.adapters import resolve_provider_config
from mediascribe.asr.registry import list_asr_providers
from mediascribe.summary import create_summary_provider, resolve_summary_runtime
from mediascribe.summary.config import TextSource


def test_copied_mock_asr_provider_is_auto_discovered(tmp_path: Path, monkeypatch) -> None:
    import mediascribe.asr.providers as asr_package
    import mediascribe.asr.registry as asr_registry

    provider_dir = tmp_path / "asr_extra"
    provider_dir.mkdir()

    source = Path("examples/custom_providers/mock_asr_provider.py").read_text(encoding="utf-8")
    source = source.replace('"mock-asr"', '"copied-mock-asr"')
    module_name = "copied_mock_asr_provider"
    module_path = provider_dir / f"{module_name}.py"
    module_path.write_text(source, encoding="utf-8")

    monkeypatch.setenv("MOCK_ASR_TOKEN", "test-token")
    monkeypatch.setattr(asr_package, "__path__", list(asr_package.__path__) + [str(provider_dir)])
    monkeypatch.setattr(asr_registry, "_ASR_PROVIDERS", dict(asr_registry._ASR_PROVIDERS))
    monkeypatch.setattr(asr_registry, "_DISCOVERY_COMPLETE", False)
    sys.modules.pop(f"mediascribe.asr.providers.{module_name}", None)

    providers = list_asr_providers()

    assert "copied-mock-asr" in providers
    config = resolve_provider_config("copied-mock-asr", language="en-US")
    provider = create_provider("copied-mock-asr", config=config)
    segments = provider.transcribe(Path("demo.wav"))
    assert segments[0].text.endswith("demo.wav (en-US)")


def test_copied_mock_summary_provider_is_auto_discovered(tmp_path: Path, monkeypatch) -> None:
    import mediascribe.summary.providers as summary_package
    import mediascribe.summary.registry as summary_registry

    provider_dir = tmp_path / "summary_extra"
    provider_dir.mkdir()

    source = Path("examples/custom_providers/mock_summary_provider.py").read_text(encoding="utf-8")
    source = source.replace('"mock-summary"', '"copied-mock-summary"')
    module_name = "copied_mock_summary_provider"
    module_path = provider_dir / f"{module_name}.py"
    module_path.write_text(source, encoding="utf-8")

    monkeypatch.setattr(summary_package, "__path__", list(summary_package.__path__) + [str(provider_dir)])
    monkeypatch.setattr(summary_registry, "_SUMMARY_PROVIDERS", dict(summary_registry._SUMMARY_PROVIDERS))
    monkeypatch.setattr(summary_registry, "_DISCOVERY_COMPLETE", False)
    sys.modules.pop(f"mediascribe.summary.providers.{module_name}", None)

    runtime = resolve_summary_runtime("mock/custom-model")

    assert runtime.provider_name == "copied-mock-summary"
    provider = create_summary_provider(runtime.provider_name, config=runtime.config)
    result = provider.summarize([TextSource(name="note", content="hello custom provider")])
    assert result.llm_model == "mock/provider-v1"
    assert result.source_names == ["note"]
    assert "hello custom provider" in result.content
