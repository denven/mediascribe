import pytest

from mediascribe.summary import create_summary_provider
from mediascribe.summary.adapters import build_summary_config, resolve_summary_api_base
from mediascribe.summary.config import LitellmSummaryConfig
from mediascribe.summary.registry import resolve_summary_runtime
from mediascribe.audio_summary_service import (
    SummaryResult,
    TextSource,
    resolve_summary_model,
    summarize_text,
    summarize_text_sources,
    write_summary_document,
)


def test_resolve_summary_model_defaults_to_local_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MEDIASCRIBE_LLM_MODEL", raising=False)

    assert resolve_summary_model() == "ollama/qwen2.5:3b"


def test_build_summary_config_resolves_local_default_api_base(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MEDIASCRIBE_LLM_MODEL", raising=False)
    monkeypatch.delenv("MEDIASCRIBE_LLM_API_BASE", raising=False)
    monkeypatch.delenv("OLLAMA_API_BASE", raising=False)
    monkeypatch.delenv("OLLAMA_HOST", raising=False)

    assert build_summary_config() == LitellmSummaryConfig(
        llm_model="ollama/qwen2.5:3b",
        api_base="http://localhost:11434",
    )


def test_resolve_summary_runtime_selects_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDIASCRIBE_LLM_MODEL", "ollama/qwen2.5:3b")
    monkeypatch.setenv("MEDIASCRIBE_LLM_API_BASE", "http://127.0.0.1:11434")

    runtime = resolve_summary_runtime()

    assert runtime.provider_name == "litellm"
    assert runtime.config == LitellmSummaryConfig(
        llm_model="ollama/qwen2.5:3b",
        api_base="http://127.0.0.1:11434",
    )


def test_resolve_summary_model_requires_matching_key_for_explicit_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

    with pytest.raises(EnvironmentError, match="ANTHROPIC_API_KEY is required"):
        resolve_summary_model("claude-sonnet-4-20250514")


def test_resolve_summary_model_uses_env_override_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MEDIASCRIBE_LLM_MODEL", "ollama/llama3.2:3b")

    assert resolve_summary_model() == "ollama/llama3.2:3b"


def test_resolve_summary_api_base_prefers_explicit_then_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MEDIASCRIBE_LLM_API_BASE", "http://127.0.0.1:22434")

    assert resolve_summary_api_base("ollama/qwen2.5:3b", "http://localhost:11434") == "http://localhost:11434"
    assert resolve_summary_api_base("ollama/qwen2.5:3b") == "http://127.0.0.1:22434"
    assert resolve_summary_api_base("gpt-5.4-mini") == "http://127.0.0.1:22434"


def test_summarize_text_sources_returns_model_and_content(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeResponse:
        choices = [type("Choice", (), {"message": type("Message", (), {"content": "summary text"})()})()]

    monkeypatch.setattr(
        "mediascribe.audio_summary_service.litellm.completion",
        lambda **kwargs: (captured.update(kwargs), FakeResponse())[-1],
    )

    result = summarize_text_sources(
        [TextSource(name="notes", content="hello world")],
        llm_model="ollama/qwen2.5:3b",
        llm_api_base="http://localhost:11434",
    )

    assert result.content == "summary text"
    assert result.llm_model == "ollama/qwen2.5:3b"
    assert result.source_names == ["notes"]
    assert result.source_references is None
    assert captured["api_base"] == "http://localhost:11434"


def test_summarize_text_returns_content_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mediascribe.audio_summary_service.summarize_text_sources",
        lambda text_sources, llm_model=None, llm_api_base=None: SummaryResult(
            content="short summary",
            llm_model="ollama/qwen2.5:3b",
            source_names=["input"],
            source_references=None,
        ),
    )

    assert summarize_text("hello") == "short summary"


def test_write_summary_document_persists_markdown(tmp_path) -> None:
    result = SummaryResult(
        content="Summary body",
        llm_model="ollama/qwen2.5:3b",
        source_names=["notes"],
        source_references=["C:\\repo\\notes.txt"],
    )

    path = write_summary_document(result, tmp_path, summary_title="Text Summary")

    assert path.exists()
    written = path.read_text(encoding="utf-8")
    assert "# Text Summary" in written
    assert "Model: ollama/qwen2.5:3b" in written
    assert "Source files: notes" in written
    assert "Source paths / URLs:" in written
    assert "- C:\\repo\\notes.txt" in written
    assert "Summary body" in written


def test_create_summary_provider_returns_litellm_provider() -> None:
    provider = create_summary_provider(
        config=LitellmSummaryConfig(
            llm_model="ollama/qwen2.5:3b",
            api_base="http://localhost:11434",
        )
    )

    assert provider.__class__.__name__ == "LitellmSummaryProvider"
