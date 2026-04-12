"""Summary provider factory backed by the provider registry."""

from mediascribe.summary.config import SummaryProviderConfig
from mediascribe.summary.registry import (
    ensure_summary_providers_loaded,
    get_summary_provider_spec,
    list_summary_providers,
)

ensure_summary_providers_loaded()
SUMMARY_PROVIDERS = list_summary_providers()


def create_summary_provider(
    name: str = "litellm",
    *,
    config: SummaryProviderConfig,
):
    """Create a summary provider by name using the discovered registry."""

    spec = get_summary_provider_spec(name)
    return spec.provider_cls(config=config)
