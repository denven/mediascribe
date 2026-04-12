"""Resolve ASR runtime configuration through the provider registry."""

from mediascribe.asr.config import ASRConfig
from mediascribe.asr.registry import get_asr_provider_spec
from mediascribe.config import DEFAULT_WHISPER_MODEL


def resolve_provider_config(
    provider_name: str,
    *,
    model_size: str = DEFAULT_WHISPER_MODEL,
    language: str | None = None,
    env: dict[str, str] | None = None,
) -> ASRConfig:
    """Build a provider config using the provider's registered resolver."""

    spec = get_asr_provider_spec(provider_name)
    return spec.config_resolver(
        model_size=model_size,
        language=language,
        env=env,
    )
