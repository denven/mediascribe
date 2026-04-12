# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaScribe is a CLI toolkit for transcribing and summarizing audio, text, and video with reusable staged workflows.

Public project and CLI branding uses `MediaScribe`. The canonical Python package namespace is `mediascribe`.

Preferred CLI commands:
- `mediascribe`
- `mediascribe-transcriber`
- `mediascribe-text`

## Tech Stack

- **Local ASR**: `faster-whisper` + `pyannote.audio`
- **Cloud ASR**: Azure Speech / Aliyun / iFlytek through a shared provider interface
- **LLM Summary**: `litellm` routing to local Ollama models or cloud LLM APIs
- **Video support**: `yt-dlp` + `ffmpeg`
- **CLI**: `argparse`
- **Python**: >= 3.10

## Development Setup

```bash
uv sync --extra local --extra dev
```

Dependencies are split into layers (see `pyproject.toml`):
- Core (`uv sync`): `litellm` + `requests`
- Video (`uv sync --extra video`): `yt-dlp`
- Local (`uv sync --extra local`): `faster-whisper` + `pyannote.audio` + PyTorch
- Dev (`uv sync --extra dev`): `pytest`

Runtime prerequisites that are not installed by `uv sync`:
- Local ASR: `ffmpeg` >= 4.4 in `PATH`, plus `HF_TOKEN` for `pyannote.audio`
- Local LLM summary: Ollama installed separately, Ollama running on `http://localhost:11434`, and a local model pulled (default: `qwen2.5:3b`)

Typical local summary setup:

```bash
ollama pull qwen2.5:3b
# If Ollama is not already running in the background:
ollama serve
```

## Running

```bash
# Audio: transcript + summary
uv run mediascribe audio.mp3 --asr azure

# Audio: transcript only
uv run mediascribe audio.mp3 --asr azure --no-summary

# Audio: transcription-focused entrypoint
uv run mediascribe-transcriber ./recordings --asr azure -o ./output

# Text: summarize existing notes or transcripts
uv run mediascribe-text ./notes

# Text: summarize with the default local Ollama model
uv run mediascribe-text ./notes --llm-model ollama/qwen2.5:3b --llm-api-base http://localhost:11434

# Video: subtitle-first summary
uv run mediascribe video "https://www.youtube.com/watch?v=aircAruvnKk"
```

## Testing

```bash
uv run pytest
uv run pytest tests/test_scanner.py -k "test_filter"
```

## Architecture

```text
mediascribe/
├── cli.py                    # Top-level mediascribe entrypoint
├── transcription_service.py  # Audio transcription orchestration
├── audio_summary_service.py  # Audio transcript summary helpers
├── text_summary_service.py   # Generic text/file summary helpers
├── video_summary_service.py  # Video orchestration
├── video_input_service.py    # Local-vs-remote video resolution
├── subtitle_fetch_service.py # Subtitle-first video path
├── media_extract_service.py  # Audio extraction/download path
├── formatter.py              # Transcript formatting and writing
├── scanner.py                # Audio input discovery
├── asr/                      # ASR provider registry, config, adapters, providers
└── summary/                  # Summary provider registry, config, adapters, providers
```

## Key Design Decisions

- **Provider-based architecture**: ASR and summary backends are isolated behind registries and typed configs.
- **Subtitle-first video flow**: video prefers subtitles, then falls back to audio extraction + ASR + summary.
- **Reusable staged workflows**: transcription, transcript summary, text summary, and video summary can be run independently.
- **Default audio behavior**: `mediascribe` summarizes by default unless `--no-summary` or `--transcript-only` is used.
- **Fail-forward batches**: multi-file transcription logs individual failures and continues.

## Code Conventions

- Use type hints on all function signatures.
- Use `logging`, not `print`, for runtime output.
- Keep configuration defaults in `mediascribe/config.py`.
- Read credentials from environment variables only.
- New providers should plug into the existing registry/discovery flow instead of branching CLI logic.

## Output Format

Transcript files use this format:

```text
[HH:MM:SS] Speaker N: <text>
```

Summary output is Markdown and keeps source-reference metadata when available.
