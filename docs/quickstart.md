# MediaScribe Quick Start

Language: **English** | [Chinese](quickstart.zh-CN.md)

This guide gets you from zero to a working transcript or summary in about 5 minutes.

## 1. Install

```bash
uv venv --python 3.11
```

Install by scenario:

```bash
# Cloud ASR + summary
uv sync

# Remote video support
uv sync --extra video

# Local ASR support
uv sync --extra local

# Local ASR + remote video
uv sync --extra local --extra video
```

For local summary generation, install Ollama, make sure it is running, and pull the default model:

```bash
ollama pull qwen2.5:3b
# If Ollama is not already running in the background:
ollama serve
```

## 2. Minimal `.env`

```env
HF_TOKEN=hf_xxx
MEDIASCRIBE_LLM_MODEL=ollama/qwen2.5:3b
MEDIASCRIBE_LLM_API_BASE=http://localhost:11434
AZURE_SPEECH_KEY=xxx
AZURE_SPEECH_REGION=westus2
```

Notes:
- `HF_TOKEN` is mainly for local ASR
- MediaScribe defaults to the local Ollama summary model `ollama/qwen2.5:3b`
- If you only want transcripts, use `--no-summary`
- If you want a cloud model instead, pass `--llm-model` and set the matching API key in `.env`

## 3. Preferred Commands

- `mediascribe`
- `mediascribe-transcriber`
- `mediascribe-text`

## 4. First Commands to Try

### Audio -> transcript + summary

```bash
uv run mediascribe ".\meeting.wav" --asr azure
```

### Audio -> transcript only

```bash
uv run mediascribe ".\meeting.wav" --asr azure --no-summary
```

### Existing transcripts -> summary only

```bash
uv run mediascribe .\output --summary-only
```

### Text directory

```bash
uv run mediascribe-text .\notes
```

### Text directory with explicit local model

```bash
uv run mediascribe-text .\notes --llm-model ollama/qwen2.5:3b --llm-api-base http://localhost:11434
```

### Video summary

```bash
uv run mediascribe video ".\lesson.mp4" --asr azure
```

## 5. Local Hardware Notes

### Local ASR

- `--asr local` uses more local CPU, GPU, and RAM
- `Whisper small` is the lightest practical local starting point
- `Whisper medium` is the current default and usually needs a more capable machine

### Local summary

- Default local summary model: `ollama/qwen2.5:3b`
- Practical starting point: `6-8 GB RAM` CPU-only or `4-6 GB VRAM`
- If your machine is weaker, try `ollama/llama3.2:1b`

### Cloud ASR / cloud summary

- Reduces local hardware usage
- May incur provider cost

## 6. Video Notes

Default video strategy:
1. try subtitles first
2. if subtitles are not usable, extract or download audio
3. run ASR when needed
4. generate summary

Extract audio only:

```bash
uv run mediascribe video ".\lesson.mp4" --extract-audio-only -o .\output
```

Then process the extracted audio later:

```bash
uv run mediascribe ".\output\media\lesson.wav" --asr azure
```

Speaker naming on the video ASR path:

```bash
uv run mediascribe video ".\lesson.mp4" --force-asr --asr azure --speaker-name Alice --speaker-name Bob
```

## 7. Remote Video Auth

```env
YTDLP_COOKIES_FILE=.\cookies\global.txt
YTDLP_COOKIES_FROM_BROWSER=chrome:Profile 12
YTDLP_SITE_COOKIE_MAP=bilibili.com=.\cookies\bilibili_profile12.txt
```

Inspect auth resolution:

```bash
uv run mediascribe doctor-video-auth "https://www.bilibili.com/video/BV1VtcYzTEZn/"
```

## 8. License

MediaScribe is licensed under the MIT License. See `../LICENSE`.

## 9. Next Reading

- Main README: `../README.md`
- Chinese quick start: `quickstart.zh-CN.md`
- Local workspace: `local-workspace.md`
- Architecture: `architecture.md`
- ASR guide: `asr.md`
- Summary guide: `summary.md`
- Benchmarks: `benchmark-notes.md`
