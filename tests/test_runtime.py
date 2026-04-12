"""Tests for runtime helpers."""

import logging

from mediascribe.runtime import (
    _LiteLLMNoiseFilter,
    _THIRD_PARTY_DEBUG_ENV,
    _configure_logger_levels,
    _is_truthy_env,
)


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


def test_is_truthy_env_understands_common_true_values(monkeypatch) -> None:
    monkeypatch.setenv(_THIRD_PARTY_DEBUG_ENV, "true")

    assert _is_truthy_env(_THIRD_PARTY_DEBUG_ENV) is True


def test_is_truthy_env_defaults_to_false(monkeypatch) -> None:
    monkeypatch.delenv(_THIRD_PARTY_DEBUG_ENV, raising=False)

    assert _is_truthy_env(_THIRD_PARTY_DEBUG_ENV) is False


def test_configure_logger_levels_keeps_third_party_debug_hidden_by_default(monkeypatch) -> None:
    monkeypatch.delenv(_THIRD_PARTY_DEBUG_ENV, raising=False)

    _configure_logger_levels(verbose=True)

    assert logging.getLogger("mediascribe").level == logging.DEBUG
    assert logging.getLogger("openai").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING


def test_configure_logger_levels_allows_third_party_debug_when_opted_in(monkeypatch) -> None:
    monkeypatch.setenv(_THIRD_PARTY_DEBUG_ENV, "1")

    _configure_logger_levels(verbose=True)

    assert logging.getLogger("openai").level == logging.DEBUG
    assert logging.getLogger("httpcore").level == logging.DEBUG
