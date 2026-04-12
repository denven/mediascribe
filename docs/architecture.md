# MediaScribe Architecture Overview

This document explains the current MediaScribe architecture using layers and call paths.

MediaScribe is intentionally split into reusable capabilities:

- transcription
- summary
- video orchestration
- provider routing
- media/subtitle extraction helpers

The public project name is `MediaScribe`. The canonical Python package namespace is `mediascribe`.

## Design goals

- Keep transcription and summary reusable as standalone services
- Let video orchestration reuse existing transcription and summary logic instead of reimplementing them
- Keep local and cloud providers isolated behind provider registries
- Keep the CLI thin so other Python code can call the same services directly

## Layered view

```text
CLI / Entry Points
  -> Orchestration Services
    -> Input Resolution / Scanning
    -> Capability Services
      -> ASR Providers
      -> Summary Providers
      -> ffmpeg / yt-dlp
    -> Output Formatting / Persistence
```

More concretely:

```text
mediascribe / mediascribe-transcriber / mediascribe-text
  -> transcription_service / audio_summary_service / text_summary_service / video_summary_service
  -> scanner / video_input_service / subtitle_fetch_service / media_extract_service
  -> asr/*
  -> summary/*
  -> formatter / runtime / config
```

## Entry points

Primary files:

- `mediascribe/cli.py`
- `mediascribe/transcription_service.py`
- `mediascribe/audio_summary_service.py`
- `mediascribe/text_summary_service.py`
- `mediascribe/video_summary_service.py`
- `mediascribe/video_auth_doctor.py`

Responsibilities:

- parse command-line arguments
- load `.env`
- initialize logging
- dispatch requests to the matching service

Preferred commands:

- `mediascribe`: main CLI for audio, summary-only, and video subcommands
- `mediascribe-transcriber`: transcription-focused entry point
- `mediascribe-text`: text-only summary entry point

## Audio transcription call path

```text
mediascribe-transcriber <input>
  -> transcription_service.run()
  -> transcribe_audio_input()
     -> scan_input()
     -> build_provider_config()
     -> asr.create_provider()
     -> provider.transcribe()
     -> formatter.format_transcript()
     -> formatter.write_transcript()
```

Key files:

- `mediascribe/transcription_service.py`
- `mediascribe/scanner.py`
- `mediascribe/formatter.py`

Key responsibilities:

- `scan_input()`: normalize a single file or a directory into a list of audio files
- `build_provider_config()`: combine CLI args and env vars into provider config
- `transcribe_audio_files()`: run transcription, format output, and write transcript files

This is the core reusable `audio -> transcript` capability. Both video workflows and staged summary flows build on it.

## ASR provider layer

```text
transcription_service
  -> asr.adapters.resolve_provider_config()
  -> asr.create_provider()
  -> asr.providers.local
  -> asr.providers.cloud.azure
  -> asr.providers.cloud.aliyun
  -> asr.providers.cloud.iflytek
```

Key files:

- `mediascribe/asr/__init__.py`
- `mediascribe/asr/registry.py`
- `mediascribe/asr/config.py`
- `mediascribe/asr/providers/local.py`
- `mediascribe/asr/providers/cloud/azure.py`
- `mediascribe/asr/providers/cloud/aliyun.py`
- `mediascribe/asr/providers/cloud/iflytek.py`

Why this is easy to extract:

- cloud providers already live under `mediascribe/asr/providers/cloud/`
- local ASR is isolated in `mediascribe/asr/providers/local.py`
- upper layers only depend on the shared registry interface

That makes it practical to extract only the cloud path or only the local path into another project later.

## Summary call paths

### Summary existing transcripts

```text
mediascribe <transcript-dir> --summary-only
  -> cli.py
  -> audio_summary_service.summarize_audio_input()
  -> summary.service.summarize_text_sources()
  -> summary.registry.resolve_summary_runtime()
  -> summary provider
  -> write_summary_document()
```

### Summarize arbitrary text

```text
mediascribe-text <file-or-dir>
  -> text_summary_service.run()
  -> summarize_text_input()
  -> summary.service.summarize_text_sources()
  -> summary provider
```

Or directly from Python:

```text
other python code
  -> summarize_raw_text_to_file()
  -> summary.service.summarize_text_sources()
  -> summary provider
```

Key files:

- `mediascribe/audio_summary_service.py`
- `mediascribe/text_summary_service.py`
- `mediascribe/summary/service.py`
- `mediascribe/summary/adapters/model_selection.py`
- `mediascribe/summary/registry.py`
- `mediascribe/summary/providers/litellm_provider.py`

Why this matters:

- transcript summary and general text summary share the same summary engine
- you can regenerate summaries without rerunning transcription
- other Python scripts can summarize existing text without going through the audio flow

## Summary provider layer

```text
summary.service
  -> summary.registry.resolve_summary_runtime()
  -> summary.providers.litellm_provider
  -> litellm
  -> provider-specific API key / model
```

Model selection logic lives in:

- `mediascribe/summary/adapters/model_selection.py`

Current behavior:

- if `--llm-model` is provided, MediaScribe validates any matching provider credentials when needed
- otherwise it falls back to the local default summary model
- the current default is `ollama/qwen2.5:3b` via `http://localhost:11434`

Benefits:

- upper layers do not hardcode OpenAI, Anthropic, Gemini, or DeepSeek details
- adding another summary provider mainly means registering it in the summary registry

## Video summary call path

```text
mediascribe video <input>
  -> video_summary_service.run()
  -> summarize_video_input()
     -> resolve_video_input()
     -> fetch_best_subtitle()
        -> local sidecar subtitles
        -> ffmpeg extraction of embedded subtitles
        -> yt-dlp subtitle download for remote video
     -> if subtitles are usable
        -> text_summary_service.summarize_text_input()
     -> else
        -> extract_audio_for_video()
           -> local: ffmpeg
           -> remote: yt-dlp + ffmpeg
        -> transcribe_audio_input()
        -> summarize_audio_input()
```

Key files:

- `mediascribe/video_summary_service.py`
- `mediascribe/video_input_service.py`
- `mediascribe/video_models.py`
- `mediascribe/subtitle_fetch_service.py`
- `mediascribe/media_extract_service.py`
- `mediascribe/yt_dlp_auth.py`

Why the video layer is orchestration-only:

- it does not implement ASR itself
- it does not implement summary generation itself
- it decides whether subtitles or audio should be used
- then it delegates to the existing text/transcription/summary services

That keeps video support additive and reduces the risk of breaking the original audio/text workflows.

## ffmpeg and yt-dlp roles

### `ffmpeg`

Used for:

- extracting audio from local video
- extracting embedded subtitles from local video
- inspecting and splitting audio for safer Azure uploads

### `yt-dlp`

Used for:

- downloading subtitles from supported remote video sites
- downloading remote audio when subtitle-first is not enough

## Video auth and cookies

The video auth helpers build yt-dlp authentication options from:

- `--yt-dlp-cookies <path>`
- `--yt-dlp-cookies-from-browser <browser-spec>`
- `YTDLP_COOKIES_FILE`
- `YTDLP_COOKIES_FROM_BROWSER`
- `YTDLP_SITE_COOKIE_MAP`

Current fallback order:

1. site-specific cookie file
2. global cookie file
3. browser-profile cookies
4. unauthenticated request

This helps when:

- subtitles require login
- audio download requires login
- a public video still needs cookies on a resource endpoint

## Output structure

Typical output:

```text
output/
|-- transcripts/
|   |-- part1.txt
|   `-- part2.txt
|-- subtitles/
|   `-- lesson.subtitle.txt
|-- media/
|   `-- lesson.wav
`-- summary.md
```

Common patterns:

- one-shot audio runs usually create `transcripts/` and `summary.md`
- video runs usually create `summary.md` unless `--extract-audio-only` is used
- extracted intermediate audio is stored under `media/`

## Current vs planned direction

Current structure already supports:

- standalone transcription
- standalone text/transcript summary
- video orchestration that reuses both services
- provider-based cloud/local separation

The main future-friendly advantage is that each capability can be extracted more easily:

- cloud ASR can be lifted from `mediascribe/asr/providers/cloud/`
- local ASR can be lifted from `mediascribe/asr/providers/local.py`
- summary can be lifted from `mediascribe/summary/`
- video can continue to stay as a higher-level orchestration layer
