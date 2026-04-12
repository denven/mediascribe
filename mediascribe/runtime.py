"""Runtime helpers shared by CLI entry points."""

import logging
import os
from pathlib import Path

_LITELLM_NOISE_MARKERS = (
    "Failed to fetch remote model cost map",
    "/api/generate/api/show",
)
_LITELLM_LOGGERS = ("LiteLLM", "LiteLLM Proxy", "LiteLLM Router")


class _LiteLLMNoiseFilter(logging.Filter):
    """Hide known non-fatal LiteLLM warnings that confuse CLI users."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        return not any(marker in message for marker in _LITELLM_NOISE_MARKERS)


def load_environment(env_path: Path | None = None) -> None:
    """Load simple KEY=VALUE pairs from a local .env file without overriding the shell."""
    env_file = env_path or Path(".env")
    if not env_file.is_file():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()

        key, sep, value = line.partition("=")
        if not sep:
            continue

        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if not value:
            continue

        os.environ.setdefault(key, value)


def _install_external_log_filters() -> None:
    """Mute specific third-party log noise while preserving actionable warnings."""
    for logger_name in _LITELLM_LOGGERS:
        logger = logging.getLogger(logger_name)
        if getattr(logger, "_mediascribe_noise_filter_installed", False):
            continue
        logger.addFilter(_LiteLLMNoiseFilter())
        logger._mediascribe_noise_filter_installed = True


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    _install_external_log_filters()
