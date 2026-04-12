"""Tests for runtime helpers."""

import logging

from mediascribe.runtime import _LiteLLMNoiseFilter


def test_litellm_noise_filter_blocks_known_model_cost_warning() -> None:
    record = logging.LogRecord(
        "LiteLLM",
        logging.WARNING,
        __file__,
        1,
        "LiteLLM: Failed to fetch remote model cost map from %s",
        ("https://example.test/model-costs.json",),
        None,
    )

    assert _LiteLLMNoiseFilter().filter(record) is False


def test_litellm_noise_filter_blocks_bad_ollama_show_url_warning() -> None:
    record = logging.LogRecord(
        "LiteLLM",
        logging.DEBUG,
        __file__,
        1,
        "OllamaError: Client error '404 Not Found' for url '%s'",
        ("http://localhost:11434/api/generate/api/show",),
        None,
    )

    assert _LiteLLMNoiseFilter().filter(record) is False


def test_litellm_noise_filter_keeps_other_messages() -> None:
    record = logging.LogRecord(
        "LiteLLM",
        logging.ERROR,
        __file__,
        1,
        "Ollama request failed with timeout",
        (),
        None,
    )

    assert _LiteLLMNoiseFilter().filter(record) is True
