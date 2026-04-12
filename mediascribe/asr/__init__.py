"""ASR provider factory and registry-backed exports."""

from mediascribe.asr.config import ASRConfig
from mediascribe.asr.registry import (
    ensure_asr_providers_loaded,
    get_asr_provider_spec,
    list_asr_providers,
)

ensure_asr_providers_loaded()
ASR_PROVIDERS = list_asr_providers()


def create_provider(name: str, *, config: ASRConfig):
    """Create an ASR provider by name using the discovered registry."""

    spec = get_asr_provider_spec(name)
    return spec.provider_cls(config=config)
