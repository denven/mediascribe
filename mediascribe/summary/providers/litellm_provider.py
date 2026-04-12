"""LiteLLM-backed summary provider implementation."""

import logging

import litellm

from mediascribe.config import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT_TEMPLATE
from mediascribe.summary.adapters.model_selection import build_summary_config
from mediascribe.summary.config import LitellmSummaryConfig, SummaryResult, TextSource
from mediascribe.summary.registry import register_summary_provider

logger = logging.getLogger(__name__)

litellm.suppress_debug_info = True


class LitellmSummaryProvider:
    """Generate summaries via LiteLLM-compatible chat models."""

    def __init__(self, config: LitellmSummaryConfig) -> None:
        self._llm_model = config.llm_model
        self._api_base = config.api_base

    def summarize(self, text_sources: list[TextSource]) -> SummaryResult:
        if not text_sources:
            raise ValueError("At least one text source is required.")

        logger.info("Generating summary using model: %s", self._llm_model)

        combined = "\n\n---\n\n".join(source.content for source in text_sources)
        source_names = [source.name for source in text_sources]
        source_references = [source.reference for source in text_sources if source.reference]
        total_characters = len(combined)
        logger.info(
            "Summary request prepared: %d source(s), %d character(s) of transcript text",
            len(text_sources),
            total_characters,
        )
        user_prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(transcripts=combined)
        completion_kwargs = {
            "model": self._llm_model,
            "messages": [
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self._api_base:
            completion_kwargs["api_base"] = self._api_base

        try:
            logger.info(
                "Summary request in progress: waiting for provider response from model %s",
                self._llm_model,
            )
            logger.debug(
                "Starting LiteLLM completion for model=%s api_base=%s",
                self._llm_model,
                self._api_base,
            )
            response = litellm.completion(**completion_kwargs)
            logger.debug("LiteLLM completion returned for model=%s", self._llm_model)
            summary_content = response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"LLM API call failed ({self._llm_model}): {e}") from e

        return SummaryResult(
            content=summary_content,
            llm_model=self._llm_model,
            source_names=source_names,
            source_references=source_references or None,
        )


register_summary_provider(
    "litellm",
    LitellmSummaryProvider,
    runtime_resolver=build_summary_config,
    priority=1000,
)
