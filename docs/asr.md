# ASR API and Extension Guide

This document describes the standalone transcription architecture, Python APIs, and how to add new ASR providers without changing the main transcription flow.

Note: the public CLI branding is `MediaScribe`, the canonical Python package path is `mediascribe`.

Preferred CLI examples:

- `uv run mediascribe-transcriber ...`
- `uv run mediascribe ... --no-summary`

## Layers

```text
caller
  -> transcription_service.py
    -> asr.adapters.config_resolver
      -> asr.registry
        -> provider-specific config resolver
    -> asr.create_provider(...)
      -> asr.registry
        -> provider class
```

Responsibilities:

- `mediascribe/transcription_service.py`: orchestration, file scanning, transcript writing
- `mediascribe/asr/adapters/`: resolve runtime config from env and call arguments
- `mediascribe/asr/config.py`: typed config dataclasses
- `mediascribe/asr/providers/`: concrete ASR implementations
- `mediascribe/asr/registry.py`: provider discovery and registration

## Built-in providers

- `local`: `mediascribe/asr/providers/local.py`
- `azure`: `mediascribe/asr/providers/cloud/azure.py`
- `aliyun`: `mediascribe/asr/providers/cloud/aliyun.py`
- `iflytek`: `mediascribe/asr/providers/cloud/iflytek.py`

Shortcut provider modules are also available at:

- `mediascribe/asr/local.py`
- `mediascribe/asr/azure.py`
- `mediascribe/asr/aliyun.py`
- `mediascribe/asr/iflytek.py`

## High-level Python APIs

Use this when you want the same behavior as the CLI.

```python
from pathlib import Path

from mediascribe.transcription_service import transcribe_audio_input

result = transcribe_audio_input(
    "meeting.wav",
    output_dir=Path("output"),
    asr_provider="azure",
    language="zh-CN",
    speaker_names=["Alice", "Bob"],
)

print(result.transcript_paths)
```

Use this when you already have audio paths and want to reuse a prepared provider:

```python
from pathlib import Path

from mediascribe.asr import create_provider
from mediascribe.transcription_service import build_provider_config, transcribe_audio_files

config = build_provider_config("azure", language="en-US")
provider = create_provider("azure", config=config)

result = transcribe_audio_files(
    [Path("meeting.wav"), Path("meeting_part2.wav")],
    provider,
    output_dir=Path("output"),
)
```

## Low-level provider APIs

Use this when another application already has its own config source and you do not want env-driven resolution.

### Local

```python
from pathlib import Path

from mediascribe.asr.config import LocalASRConfig
from mediascribe.asr.providers.local import LocalASRProvider

provider = LocalASRProvider(
    LocalASRConfig(
        model_size="medium",
        language="zh",
        hf_token="hf_xxx",
    )
)
segments = provider.transcribe(Path("meeting.wav"))
```

### Azure

```python
from pathlib import Path

from mediascribe.asr.config import AzureASRConfig
from mediascribe.asr.providers.cloud.azure import AzureASRProvider

provider = AzureASRProvider(
    AzureASRConfig(
        key="your-key",
        region="eastus",
        language="en-US",
    )
)
segments = provider.transcribe(Path("meeting.wav"))
```

## Config resolution

The main orchestration path calls:

```python
from mediascribe.transcription_service import build_provider_config

config = build_provider_config("azure", language="en-US")
```

Internally this delegates to the registered provider-specific resolver, so adding a new provider does not require editing the orchestration layer.

## Azure locale note

When you pass `language=` in Python or `-l/--language` in the CLI with `--asr azure`, use a supported Azure Speech locale in BCP-47 form, such as `zh-CN`, `en-US`, `ja-JP`, or `fr-FR`.

Do not use short language codes such as `zh` or `en` for Azure fast transcription. Azure can reject them with `InvalidLocale`.

Official locale reference:

- Azure Speech language support (Speech to text / fast transcription locales): https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=stt

## How to add a new ASR provider

1. Add a config dataclass in `mediascribe/asr/config.py`
2. Create a provider module under `mediascribe/asr/providers/`
3. Implement:
   - a provider class with `transcribe(self, audio_path)`
   - a config resolver function
4. Register both in that module with `register_asr_provider(...)`
5. Optionally add a shortcut module under `mediascribe/asr/`

Example skeleton:

```python
import os
from pathlib import Path

from mediascribe.asr.adapters.env import clean_env_value
from mediascribe.asr.config import MyASRConfig
from mediascribe.asr.registry import register_asr_provider


class MyASRProvider:
    def __init__(self, config: MyASRConfig) -> None:
        self._token = config.token

    def transcribe(self, audio_path: Path):
        ...


def resolve_my_asr_config(*, model_size=None, language=None, env=None) -> MyASRConfig:
    env_map = env if env is not None else os.environ
    return MyASRConfig(
        token=clean_env_value(env_map.get("MY_ASR_TOKEN")),
        language=language,
    )


register_asr_provider(
    "my-asr",
    MyASRProvider,
    config_resolver=resolve_my_asr_config,
)
```

Once the module is placed under `mediascribe/asr/providers/`, discovery loads it automatically.

Copyable example:

- `examples/custom_providers/mock_asr_provider.py`
- `examples/custom_providers/http_webhook_asr_provider.py`
- Third-party integration guide: `docs/plugin-providers.md`

## Notes for extraction into another project

If you only want cloud providers, the smallest useful slice is usually:

- `mediascribe/asr/config.py`
- `mediascribe/asr/registry.py`
- `mediascribe/asr/adapters/env.py`
- `mediascribe/asr/providers/cloud/`

If you only want local transcription:

- `mediascribe/asr/config.py`
- `mediascribe/asr/registry.py`
- `mediascribe/asr/adapters/env.py`
- `mediascribe/asr/providers/local.py`
