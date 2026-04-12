"""Pluggable summary provider registry with provider discovery."""

from collections.abc import Callable
from dataclasses import dataclass
from importlib import import_module
from pkgutil import walk_packages

from mediascribe.summary.config import SummaryProviderConfig
from mediascribe.summary.providers.base import SummaryProvider


SummaryRuntimeResolver = Callable[..., SummaryProviderConfig | None]


@dataclass(frozen=True)
class SummaryProviderSpec:
    name: str
    provider_cls: type[SummaryProvider]
    runtime_resolver: SummaryRuntimeResolver
    priority: int


@dataclass(frozen=True)
class SummaryRuntime:
    provider_name: str
    config: SummaryProviderConfig


_SUMMARY_PROVIDERS: dict[str, SummaryProviderSpec] = {}
_DISCOVERY_COMPLETE = False


def register_summary_provider(
    name: str,
    provider_cls: type[SummaryProvider],
    *,
    runtime_resolver: SummaryRuntimeResolver,
    priority: int = 100,
) -> None:
    """Register a summary provider and its runtime resolver."""

    _SUMMARY_PROVIDERS[name] = SummaryProviderSpec(
        name=name,
        provider_cls=provider_cls,
        runtime_resolver=runtime_resolver,
        priority=priority,
    )


def ensure_summary_providers_loaded() -> None:
    """Import provider modules once so they can self-register."""

    global _DISCOVERY_COMPLETE
    if _DISCOVERY_COMPLETE:
        return

    package = import_module("mediascribe.summary.providers")
    for module_info in walk_packages(package.__path__, prefix=f"{package.__name__}."):
        import_module(module_info.name)

    _DISCOVERY_COMPLETE = True


def get_summary_provider_spec(name: str) -> SummaryProviderSpec:
    """Return a registered summary provider spec by name."""

    ensure_summary_providers_loaded()
    spec = _SUMMARY_PROVIDERS.get(name)
    if spec is None:
        available = ", ".join(sorted(_SUMMARY_PROVIDERS))
        raise ValueError(f"Unknown summary provider: '{name}'. Available: {available}")
    return spec


def list_summary_providers() -> dict[str, type[SummaryProvider]]:
    """Return the discovered summary providers keyed by provider name."""

    ensure_summary_providers_loaded()
    return {
        name: spec.provider_cls
        for name, spec in sorted(_SUMMARY_PROVIDERS.items())
    }


def resolve_summary_runtime(
    llm_model: str | None = None,
    llm_api_base: str | None = None,
) -> SummaryRuntime:
    """Resolve which summary provider should handle the current request."""

    ensure_summary_providers_loaded()
    last_error: Exception | None = None
    ordered_specs = sorted(
        _SUMMARY_PROVIDERS.items(),
        key=lambda item: (item[1].priority, item[0]),
    )
    for name, spec in ordered_specs:
        try:
            config = spec.runtime_resolver(llm_model=llm_model, llm_api_base=llm_api_base)
        except EnvironmentError as exc:
            last_error = exc
            continue
        if config is not None:
            return SummaryRuntime(provider_name=name, config=config)

    if last_error is not None:
        raise last_error
    available = ", ".join(sorted(_SUMMARY_PROVIDERS))
    raise RuntimeError(f"No summary provider could resolve the request. Available: {available}")
