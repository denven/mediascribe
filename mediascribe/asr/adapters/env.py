"""Shared environment helpers for ASR adapters and provider config resolution."""


def clean_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
