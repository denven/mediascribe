"""Typed ASR provider configuration objects."""

from dataclasses import dataclass

from mediascribe.config import DEFAULT_WHISPER_MODEL


@dataclass(frozen=True)
class LocalASRConfig:
    """Runtime configuration for the local Whisper + pyannote provider."""

    model_size: str = DEFAULT_WHISPER_MODEL
    language: str | None = None
    hf_token: str | None = None


@dataclass(frozen=True)
class AzureASRConfig:
    """Runtime configuration for Azure Speech transcription."""

    key: str | None
    region: str | None = None
    endpoint: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class AliyunASRConfig:
    """Runtime configuration for Alibaba Cloud transcription."""

    access_key_id: str | None
    access_key_secret: str | None
    appkey: str | None
    language: str | None = None


@dataclass(frozen=True)
class IflytekASRConfig:
    """Runtime configuration for iFlytek transcription."""

    app_id: str | None
    api_key: str | None
    language: str | None = None


ASRConfig = LocalASRConfig | AzureASRConfig | AliyunASRConfig | IflytekASRConfig


def resolve_provider_config(*args, **kwargs) -> ASRConfig:
    """Resolve provider config via the adapter layer."""

    from mediascribe.asr.adapters.config_resolver import resolve_provider_config as _resolve

    return _resolve(*args, **kwargs)
