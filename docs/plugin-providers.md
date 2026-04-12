# Third-Party Provider Integration Guide

This guide explains how to add external ASR or summary providers to MediaScribe without modifying the main orchestration flow.

Note: MediaScribe is the public project/CLI name, the canonical Python package namespace is `mediascribe`.

## Design goals

The current architecture is built around three ideas:

1. orchestration code should stay stable
2. provider-specific config parsing should live with the provider
3. new providers should register themselves through discovery

That means a third-party integration should usually only need:

- a config dataclass
- a provider implementation
- a resolver / router
- one registration call

## ASR provider contract

An ASR provider must:

- accept a typed config object in `__init__`
- implement `transcribe(self, audio_path: Path) -> list[TranscribedSegment]`
- register itself with `register_asr_provider(...)`

Typical file placement:

- `mediascribe/asr/providers/my_provider.py`
- or `mediascribe/asr/providers/cloud/my_provider.py`

Typical registration flow:

```python
register_asr_provider(
    "my-asr",
    MyASRProvider,
    config_resolver=resolve_my_asr_config,
)
```

## Summary provider contract

A summary provider must:

- accept a typed config object in `__init__`
- implement `summarize(self, text_sources) -> SummaryResult`
- provide a runtime resolver that either:
  - returns a config object when it wants to handle the request
  - returns `None` when another provider should handle it
- register itself with `register_summary_provider(...)`

Typical registration flow:

```python
register_summary_provider(
    "my-summary",
    MySummaryProvider,
    runtime_resolver=resolve_my_summary_runtime,
)
```

## Routing guidance

When you write a resolver, keep it narrow.

Good examples:

- only claim `llm_model` values with your provider prefix
- only activate when your required env vars are present
- return `None` when the request should fall through to another provider

Avoid:

- claiming every request by default
- raising errors for requests that clearly belong to another provider

## Error-handling guidance

Prefer these patterns:

- `EnvironmentError` for missing credentials or runtime prerequisites
- `RuntimeError` for provider API failures or invalid remote responses
- normalize provider-specific errors into clear actionable messages

For ASR, return normalized `TranscribedSegment` values instead of leaking raw vendor payloads.

For summary providers, return normalized `SummaryResult` values instead of raw SDK responses.

## Discovery rules

Provider discovery only scans these runtime package trees:

- `mediascribe/asr/providers/`
- `mediascribe/summary/providers/`

Files under `examples/` are intentionally not auto-discovered.

That is why the mock templates in `examples/custom_providers/` are safe to keep in the repo as documentation.

## Recommended development workflow

1. Start from:
   - `examples/custom_providers/mock_asr_provider.py`
   - `examples/custom_providers/mock_summary_provider.py`
   - `examples/custom_providers/http_webhook_asr_provider.py`
   - `examples/custom_providers/openai_responses_summary_provider.py`
2. Copy the file into the real provider package
3. Replace mock config fields and env vars
4. Replace the fake implementation with your actual SDK / HTTP / local-model code
5. Add focused tests for routing, config resolution, and normalized output

## Testing checklist

For ASR providers:

- config resolver trims env values correctly
- missing credentials fail with a clear message
- `transcribe()` returns normalized `TranscribedSegment` items
- error payloads are surfaced in a readable way

For summary providers:

- runtime resolver only claims matching requests
- missing credentials fail with a clear message
- `summarize()` returns a normalized `SummaryResult`
- the resolved provider and model metadata are preserved

## Where to document new providers

When you add a real provider, update:

- `docs/asr.md` or `docs/summary.md`
- `README.md` if the provider is user-facing
- `.env.example` if it introduces new env vars
