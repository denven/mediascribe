"""Manual integration check for the local Ollama summary path.

Usage:
    uv run python scripts/manual_check_ollama_summary.py

This script:
1. loads `.env`
2. checks whether the Ollama API is reachable
3. checks whether the requested model is available locally
4. runs a real summary through MediaScribe's public text summary API
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

from mediascribe.config import DEFAULT_LLM_API_BASE, DEFAULT_LLM_MODEL
from mediascribe.runtime import load_environment, setup_logging
from mediascribe.text_summary_service import summarize_raw_text_to_file

DEFAULT_TEXT = (
    "Team sync notes. We agreed to ship the CLI cleanup this week. "
    "The README and quickstart are now split by language. "
    "The default local summary model should be Ollama with qwen2.5:3b. "
    "Next actions: verify the local summary path, improve error messages, "
    "and do one final repository cleanup pass."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a real local summary against Ollama using the current MediaScribe wiring.",
    )
    parser.add_argument(
        "--text",
        default=DEFAULT_TEXT,
        help="Raw text to summarize.",
    )
    parser.add_argument(
        "--llm-model",
        default=DEFAULT_LLM_MODEL,
        help=f"LiteLLM model name (default: {DEFAULT_LLM_MODEL}).",
    )
    parser.add_argument(
        "--llm-api-base",
        default=DEFAULT_LLM_API_BASE,
        help=f"Ollama API base (default: {DEFAULT_LLM_API_BASE}).",
    )
    parser.add_argument(
        "--output-dir",
        default="manual_checks/ollama_summary",
        help="Directory where the generated summary will be written.",
    )
    parser.add_argument(
        "--source-name",
        default="manual-ollama-check",
        help="Logical source name written into the summary metadata.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    return parser


def ollama_model_name(llm_model: str) -> str:
    if llm_model.startswith("ollama/"):
        return llm_model.split("/", 1)[1]
    return llm_model


def ensure_ollama_ready(llm_model: str, llm_api_base: str) -> None:
    tags_url = llm_api_base.rstrip("/") + "/api/tags"
    try:
        response = requests.get(tags_url, timeout=5)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            "Could not reach the Ollama API. "
            f"Expected it at {tags_url}. Start Ollama first, then retry."
        ) from exc

    payload = response.json()
    models = {
        item.get("name", "").strip()
        for item in payload.get("models", [])
        if item.get("name")
    }
    requested_model = ollama_model_name(llm_model)
    if requested_model not in models:
        available = ", ".join(sorted(models)) or "(none)"
        raise RuntimeError(
            f"Ollama is running, but model `{requested_model}` is not available locally.\n"
            f"Available models: {available}\n"
            f"Run `ollama pull {requested_model}` and retry."
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    load_environment()
    setup_logging(args.verbose)

    ensure_ollama_ready(args.llm_model, args.llm_api_base)

    output_dir = Path(args.output_dir)
    summary_path = summarize_raw_text_to_file(
        text=args.text,
        output_dir=output_dir,
        source_name=args.source_name,
        llm_model=args.llm_model,
        llm_api_base=args.llm_api_base,
        summary_title="Manual Ollama Summary Check",
    )

    print(f"Summary written to: {summary_path}")
    print("")
    print(summary_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
