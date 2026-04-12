"""Copyable example of a custom ASR provider.

This file is not auto-discovered where it currently lives.
To enable it, copy it into `mediascribe/asr/providers/`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from mediascribe.asr.adapters.env import clean_env_value
from mediascribe.asr.registry import register_asr_provider
from mediascribe.models import TranscribedSegment


@dataclass(frozen=True)
class MockASRConfig:
    api_token: str | None
    language: str | None = None


class MockASRProvider:
    """Minimal example provider that returns canned transcript content."""

    def __init__(self, config: MockASRConfig) -> None:
        self._api_token = config.api_token
        self._language = config.language

    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        if not self._api_token:
            raise EnvironmentError(
                "MOCK_ASR_TOKEN is required for the mock ASR provider.\n"
                "Replace this with your real provider credential checks."
            )

        # Real HTTP API integration usually looks like this:
        # 1. Read bytes from `audio_path`
        # 2. Call your vendor SDK / REST endpoint
        # 3. Poll until transcription is ready if the API is async
        # 4. Map the provider response into `TranscribedSegment`
        #
        # Example sketch:
        #
        # audio_bytes = audio_path.read_bytes()
        # response = requests.post(
        #     "https://api.example.com/transcribe",
        #     headers={"Authorization": f"Bearer {self._api_token}"},
        #     files={"file": (audio_path.name, audio_bytes, "audio/wav")},
        #     data={"language": self._language or "auto"},
        #     timeout=300,
        # )
        # payload = response.json()
        # return [
        #     TranscribedSegment(
        #         start=item["start"],
        #         end=item["end"],
        #         speaker=item.get("speaker", "Speaker 1"),
        #         text=item["text"].strip(),
        #     )
        #     for item in payload["segments"]
        # ]
        #
        # Real local-model integration usually looks like this:
        # 1. Load your model once in `__init__` or lazily on first call
        # 2. Run inference on `audio_path`
        # 3. Normalize the model output into `TranscribedSegment`

        return [
            TranscribedSegment(
                start=0.0,
                end=2.5,
                speaker="Speaker 1",
                text=f"[mock transcript via token] {audio_path.name} ({self._language or 'auto'})",
            )
        ]


def resolve_mock_asr_config(
    *,
    model_size: str | None = None,
    language: str | None = None,
    env: dict[str, str] | None = None,
) -> MockASRConfig:
    """Resolve mock provider config from env and call arguments."""

    del model_size
    env_map = env if env is not None else os.environ
    # Add more fields here if your provider needs them, for example:
    # - endpoint URLs
    # - project IDs / regions
    # - model names
    # - optional diarization switches
    return MockASRConfig(
        api_token=clean_env_value(env_map.get("MOCK_ASR_TOKEN")),
        language=language,
    )


register_asr_provider(
    "mock-asr",
    MockASRProvider,
    config_resolver=resolve_mock_asr_config,
)
