"""Concrete custom summary skeleton using the OpenAI Responses API.

This file is not auto-discovered where it currently lives.
To enable it, copy it into `mediascribe/summary/providers/`.

It is intentionally routed only for models that start with
`openai-responses/`, so it will not steal requests from the default
LiteLLM summary provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

from mediascribe.config import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT_TEMPLATE
from mediascribe.summary.config import SummaryResult, TextSource
from mediascribe.summary.registry import register_summary_provider

_DEFAULT_BASE_URL = "https://api.openai.com/v1"


@dataclass(frozen=True)
class OpenAIResponsesSummaryConfig:
    api_key: str | None
    model: str
    base_url: str = _DEFAULT_BASE_URL
    timeout_sec: int = 120


class OpenAIResponsesSummaryProvider:
    """Summary provider that calls the OpenAI Responses REST API directly."""

    def __init__(self, config: OpenAIResponsesSummaryConfig) -> None:
        self._api_key = config.api_key
        self._model = config.model
        self._base_url = config.base_url.rstrip("/")
        self._timeout_sec = config.timeout_sec

    def summarize(self, text_sources: list[TextSource]) -> SummaryResult:
        if not self._api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is required for the OpenAI Responses summary provider."
            )
        if not text_sources:
            raise ValueError("At least one text source is required.")

        combined = "\n\n---\n\n".join(source.content for source in text_sources)
        source_names = [source.name for source in text_sources]
        user_prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(transcripts=combined)

        response = requests.post(
            f"{self._base_url}/responses",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._model,
                "input": [
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=self._timeout_sec,
        )
        response.raise_for_status()
        payload = response.json()

        content = _extract_output_text(payload)
        if not content:
            raise RuntimeError("OpenAI Responses API returned no text output.")

        return SummaryResult(
            content=content,
            llm_model=f"openai-responses/{self._model}",
            source_names=source_names,
        )


def resolve_openai_responses_runtime(
    *,
    llm_model: str | None = None,
) -> OpenAIResponsesSummaryConfig | None:
    """Route `openai-responses/*` models to this provider."""

    if llm_model is None or not llm_model.startswith("openai-responses/"):
        return None

    model_name = llm_model.split("/", 1)[1].strip()
    if not model_name:
        raise EnvironmentError(
            "An explicit OpenAI Responses model is required, for example "
            "`openai-responses/gpt-5.4-mini`."
        )
    timeout_raw = os.environ.get("OPENAI_RESPONSES_TIMEOUT", "").strip()
    timeout_sec = int(timeout_raw) if timeout_raw else 120
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or _DEFAULT_BASE_URL
    api_key = os.environ.get("OPENAI_API_KEY", "").strip() or None

    return OpenAIResponsesSummaryConfig(
        api_key=api_key,
        model=model_name,
        base_url=base_url,
        timeout_sec=timeout_sec,
    )


def _extract_output_text(payload: dict) -> str:
    direct = payload.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    chunks: list[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                text = str(content.get("text", "")).strip()
                if text:
                    chunks.append(text)
    return "\n".join(chunks).strip()


register_summary_provider(
    "openai-responses",
    OpenAIResponsesSummaryProvider,
    runtime_resolver=resolve_openai_responses_runtime,
    priority=100,
)
