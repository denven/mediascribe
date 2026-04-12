"""Resolve summary provider configuration from environment variables and options."""

import os

from mediascribe.config import DEFAULT_LLM_API_BASE, DEFAULT_LLM_MODEL
from mediascribe.summary.config import LitellmSummaryConfig


def _get_env_value(env_var: str) -> str:
    return os.environ.get(env_var, "").strip()


def required_api_key_for_model(llm_model: str) -> str | None:
    model = llm_model.strip().lower()
    provider_prefixes = (
        ("ANTHROPIC_API_KEY", ("claude", "anthropic/")),
        ("OPENAI_API_KEY", ("gpt-", "openai/", "o1", "o3", "o4")),
        ("GEMINI_API_KEY", ("gemini", "google/", "vertex_ai/")),
        ("DEEPSEEK_API_KEY", ("deepseek",)),
    )
    for env_var, prefixes in provider_prefixes:
        if any(model.startswith(prefix) for prefix in prefixes):
            return env_var
    return None


def resolve_summary_model(llm_model: str | None = None) -> str:
    """Pick a usable summary model based on CLI, env, then local default."""

    if llm_model:
        env_var = required_api_key_for_model(llm_model)
        if env_var and not _get_env_value(env_var):
            raise EnvironmentError(
                f"{env_var} is required for summary model `{llm_model}`.\n"
                "Please fill that key in `.env`, or choose a model for a provider you have configured."
            )
        return llm_model

    env_model = _get_env_value("MEDIASCRIBE_LLM_MODEL")
    if env_model:
        env_var = required_api_key_for_model(env_model)
        if env_var and not _get_env_value(env_var):
            raise EnvironmentError(
                f"{env_var} is required for summary model `{env_model}`.\n"
                "Please fill that key in `.env`, or choose a model for a provider you have configured."
            )
        return env_model

    return DEFAULT_LLM_MODEL


def resolve_summary_api_base(
    llm_model: str,
    llm_api_base: str | None = None,
) -> str | None:
    """Resolve an optional LiteLLM api_base for local or custom endpoints."""

    if llm_api_base:
        return llm_api_base

    for env_var in ("MEDIASCRIBE_LLM_API_BASE", "OLLAMA_API_BASE", "OLLAMA_HOST"):
        env_value = _get_env_value(env_var)
        if env_value:
            return env_value

    if llm_model.strip().lower().startswith("ollama/"):
        return DEFAULT_LLM_API_BASE

    return None


def build_summary_config(
    llm_model: str | None = None,
    llm_api_base: str | None = None,
) -> LitellmSummaryConfig:
    """Resolve a concrete summary runtime config for the default provider."""

    model = resolve_summary_model(llm_model)
    return LitellmSummaryConfig(
        llm_model=model,
        api_base=resolve_summary_api_base(model, llm_api_base),
    )
