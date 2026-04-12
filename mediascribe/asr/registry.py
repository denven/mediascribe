"""Pluggable ASR provider registry with provider discovery."""

from dataclasses import dataclass
from importlib import import_module
from pkgutil import walk_packages
from typing import Callable

from mediascribe.asr.base import ASRProvider
from mediascribe.asr.config import ASRConfig


ASRConfigResolver = Callable[..., ASRConfig]


@dataclass(frozen=True)
class ASRProviderSpec:
    name: str
    provider_cls: type[ASRProvider]
    config_resolver: ASRConfigResolver


_ASR_PROVIDERS: dict[str, ASRProviderSpec] = {}
_DISCOVERY_COMPLETE = False


def register_asr_provider(
    name: str,
    provider_cls: type[ASRProvider],
    *,
    config_resolver: ASRConfigResolver,
) -> None:
    """Register an ASR provider and its config resolver."""

    _ASR_PROVIDERS[name] = ASRProviderSpec(
        name=name,
        provider_cls=provider_cls,
        config_resolver=config_resolver,
    )


def ensure_asr_providers_loaded() -> None:
    """Import provider modules once so they can self-register."""

    global _DISCOVERY_COMPLETE
    if _DISCOVERY_COMPLETE:
        return

    package = import_module("mediascribe.asr.providers")
    for module_info in walk_packages(package.__path__, prefix=f"{package.__name__}."):
        import_module(module_info.name)

    _DISCOVERY_COMPLETE = True


def get_asr_provider_spec(name: str) -> ASRProviderSpec:
    """Return a registered provider spec by name."""

    ensure_asr_providers_loaded()
    spec = _ASR_PROVIDERS.get(name)
    if spec is None:
        available = ", ".join(sorted(_ASR_PROVIDERS))
        raise ValueError(f"Unknown ASR provider: '{name}'. Available: {available}")
    return spec


def list_asr_providers() -> dict[str, type[ASRProvider]]:
    """Return the discovered ASR providers keyed by provider name."""

    ensure_asr_providers_loaded()
    return {
        name: spec.provider_cls
        for name, spec in sorted(_ASR_PROVIDERS.items())
    }
