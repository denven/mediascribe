"""Concrete custom ASR skeleton for an HTTP webhook backend.

This file is not auto-discovered where it currently lives.
To enable it, copy it into `mediascribe/asr/providers/`.

Expected remote response shape:
{
  "segments": [
    {"start": 0.0, "end": 1.2, "speaker": "Speaker 1", "text": "..."}
  ]
}
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import requests

from mediascribe.asr.adapters.env import clean_env_value
from mediascribe.asr.registry import register_asr_provider
from mediascribe.models import TranscribedSegment


@dataclass(frozen=True)
class HttpWebhookASRConfig:
    endpoint: str | None
    api_key: str | None = None
    language: str | None = None
    timeout_sec: int = 300
    response_path: str = "segments"
    text_field: str = "text"
    speaker_field: str = "speaker"
    start_field: str = "start"
    end_field: str = "end"


class HttpWebhookASRProvider:
    """Send audio to a generic HTTP transcription webhook."""

    def __init__(self, config: HttpWebhookASRConfig) -> None:
        self._endpoint = (config.endpoint or "").rstrip("/")
        self._api_key = config.api_key
        self._language = config.language
        self._timeout_sec = config.timeout_sec
        self._response_path = config.response_path
        self._text_field = config.text_field
        self._speaker_field = config.speaker_field
        self._start_field = config.start_field
        self._end_field = config.end_field

    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        if not self._endpoint:
            raise EnvironmentError(
                "WEBHOOK_ASR_URL is required for the HTTP webhook ASR provider."
            )

        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        with audio_path.open("rb") as audio_file:
            response = requests.post(
                self._endpoint,
                headers=headers,
                data={"language": self._language or "auto"},
                files={"file": (audio_path.name, audio_file, "application/octet-stream")},
                timeout=self._timeout_sec,
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text.strip()
            if detail:
                raise RuntimeError(f"Webhook ASR request failed: {detail}") from exc
            raise RuntimeError("Webhook ASR request failed.") from exc

        payload = response.json()
        segments = _get_by_dotted_path(payload, self._response_path)
        if not isinstance(segments, list):
            raise RuntimeError(
                "Webhook ASR response must include a segment list at "
                f"`{self._response_path}`."
            )

        normalized: list[TranscribedSegment] = []
        for item in segments:
            if not isinstance(item, dict):
                continue
            text = str(item.get(self._text_field, "")).strip()
            if not text:
                continue
            normalized.append(
                TranscribedSegment(
                    start=float(item.get(self._start_field, 0.0)),
                    end=float(item.get(self._end_field, 0.0)),
                    speaker=str(item.get(self._speaker_field, "Speaker 1")),
                    text=text,
                )
            )
        return normalized


def resolve_http_webhook_asr_config(
    *,
    model_size: str | None = None,
    language: str | None = None,
    env: dict[str, str] | None = None,
) -> HttpWebhookASRConfig:
    """Resolve generic webhook settings from environment variables."""

    del model_size
    env_map = env if env is not None else os.environ
    timeout_raw = clean_env_value(env_map.get("WEBHOOK_ASR_TIMEOUT"))
    timeout_sec = int(timeout_raw) if timeout_raw else 300
    return HttpWebhookASRConfig(
        endpoint=clean_env_value(env_map.get("WEBHOOK_ASR_URL")),
        api_key=clean_env_value(env_map.get("WEBHOOK_ASR_KEY")),
        language=language,
        timeout_sec=timeout_sec,
        response_path=clean_env_value(env_map.get("WEBHOOK_ASR_RESPONSE_PATH")) or "segments",
        text_field=clean_env_value(env_map.get("WEBHOOK_ASR_TEXT_FIELD")) or "text",
        speaker_field=clean_env_value(env_map.get("WEBHOOK_ASR_SPEAKER_FIELD")) or "speaker",
        start_field=clean_env_value(env_map.get("WEBHOOK_ASR_START_FIELD")) or "start",
        end_field=clean_env_value(env_map.get("WEBHOOK_ASR_END_FIELD")) or "end",
    )


def _get_by_dotted_path(payload: dict, dotted_path: str):
    current = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


register_asr_provider(
    "http-webhook-asr",
    HttpWebhookASRProvider,
    config_resolver=resolve_http_webhook_asr_config,
)
