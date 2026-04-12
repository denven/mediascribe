# Summary API and Extension Guide

This document describes the standalone summary architecture, Python APIs, and how to add new summary backends without changing the main summary flow.

Note: the public CLI branding is `MediaScribe`, the canonical Python package path is `mediascribe`.

Preferred CLI examples:

- `uv run mediascribe-text ...`
- `uv run mediascribe ... --summary-only`

## Layers

```text
caller
  -> summary.service
    -> summary.registry.resolve_summary_runtime(...)
      -> provider-specific runtime resolver
    -> summary.create_summary_provider(...)
      -> summary.registry
        -> provider class
```

Responsibilities:

- `mediascribe/summary/service.py`: generic summary orchestration
- `mediascribe/summary/adapters/`: env/model selection helpers
- `mediascribe/summary/config.py`: summary data and config dataclasses
- `mediascribe/summary/providers/`: concrete summary backends
- `mediascribe/summary/registry.py`: provider discovery and registration
- `mediascribe/audio_summary_service.py`: audio transcript summary helpers

## Built-in provider

- `litellm`: `mediascribe/summary/providers/litellm_provider.py`

## Local summary prerequisites

The default local summary path is Ollama-backed, so the Python package install is not enough by itself.

- install the Python dependencies with `uv sync`
- install Ollama separately on the machine
- make sure Ollama is running on `http://localhost:11434`
- pull at least one local model, for example `qwen2.5:3b`

Typical setup:

```bash
ollama pull qwen2.5:3b
# If Ollama is not already running in the background:
ollama serve
```

## High-level Python APIs

### Summarize existing transcript or text files

```python
from pathlib import Path

from mediascribe.text_summary_service import summarize_text_input

summary_path = summarize_text_input(
    "output/transcripts",
    output_dir=Path("output"),
    llm_model="ollama/qwen2.5:3b",
    llm_api_base="http://localhost:11434",
)
```

### Summarize raw text directly

```python
from pathlib import Path

from mediascribe.text_summary_service import summarize_raw_text_to_file

summary_path = summarize_raw_text_to_file(
    "Long text to summarize",
    output_dir=Path("manual_output"),
    source_name="manual-note",
    llm_model="ollama/qwen2.5:3b",
    llm_api_base="http://localhost:11434",
)
```

### Use the generic provider-based summary service

```python
from mediascribe.summary.config import TextSource
from mediascribe.summary.service import summarize_text_sources

result = summarize_text_sources(
    [
        TextSource(name="meeting", content="..."),
        TextSource(name="notes", content="..."),
    ],
    llm_model="ollama/qwen2.5:3b",
    llm_api_base="http://localhost:11434",
)

print(result.llm_model)
print(result.content)
```

## Runtime resolution

The default flow does two things:

1. resolve which summary provider should handle the request
2. build that provider's concrete config object

The built-in LiteLLM path is available directly:

```python
from mediascribe.summary.adapters import build_summary_config, resolve_summary_model

llm_model = resolve_summary_model()
config = build_summary_config(llm_model)
```

The provider-agnostic path is:

```python
from mediascribe.summary import resolve_summary_runtime

runtime = resolve_summary_runtime("ollama/qwen2.5:3b", "http://localhost:11434")
print(runtime.provider_name)
print(runtime.config)
```

## How to add a new summary provider

1. Add a config dataclass in `mediascribe/summary/config.py`
2. Create a provider module under `mediascribe/summary/providers/`
3. Implement:
   - a provider class with `summarize(self, text_sources)`
   - a runtime resolver function that returns the config or `None`
4. Register both in that module with `register_summary_provider(...)`

Example skeleton:

```python
from mediascribe.summary.config import MySummaryConfig, SummaryResult
from mediascribe.summary.registry import register_summary_provider


class MySummaryProvider:
    def __init__(self, config: MySummaryConfig) -> None:
        self._endpoint = config.endpoint

    def summarize(self, text_sources):
        return SummaryResult(
            content="...",
            llm_model="my-provider-model",
            source_names=[source.name for source in text_sources],
        )


def resolve_my_summary_runtime(*, llm_model=None):
    if llm_model and not llm_model.startswith("my-provider/"):
        return None
    return MySummaryConfig(endpoint="https://example.test")


register_summary_provider(
    "my-provider",
    MySummaryProvider,
    runtime_resolver=resolve_my_summary_runtime,
)
```

Once the module is placed under `mediascribe/summary/providers/`, discovery loads it automatically.

Copyable example:

- `examples/custom_providers/mock_summary_provider.py`
- `examples/custom_providers/openai_responses_summary_provider.py`
- Third-party integration guide: `docs/plugin-providers.md`

## Notes for extraction into another project

The smallest useful slice for the current summary stack is usually:

- `mediascribe/summary/config.py`
- `mediascribe/summary/registry.py`
- `mediascribe/summary/adapters/model_selection.py`
- `mediascribe/summary/providers/litellm_provider.py`
- `mediascribe/summary/service.py`

If another project already has its own key management and model selection, it can skip the adapters layer and construct provider config objects directly.
