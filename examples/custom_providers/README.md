# MediaScribe Custom Provider Examples

These examples are intentionally stored outside the runtime auto-discovery paths, so they do not affect normal MediaScribe CLI behavior.

Use them as copyable templates:

- `mock_asr_provider.py`: smallest custom ASR provider example
- `mock_summary_provider.py`: smallest custom summary provider example
- `http_webhook_asr_provider.py`: ASR skeleton for a generic HTTP webhook
- `openai_responses_summary_provider.py`: summary skeleton for the OpenAI Responses API

Recommended reading order:

1. `mock_asr_provider.py` or `mock_summary_provider.py` for the smallest possible shape
2. `http_webhook_asr_provider.py` or `openai_responses_summary_provider.py` for a more realistic integration
3. `docs/plugin-providers.md` for the full contract and testing checklist

Recommended workflow:

1. Copy the example file into the matching runtime package:
   - ASR: `mediascribe/asr/providers/`
   - Summary: `mediascribe/summary/providers/`
2. Replace the mock config fields and environment variable names
3. Replace the fake implementation with your real API / model logic
4. Keep the `register_*_provider(...)` call so discovery can find it automatically

Notes:

- Public project branding is `MediaScribe`
- Canonical imports and package paths now use `mediascribe`

