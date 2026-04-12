# MediaScribe Roadmap

This is a compact, implementation-aware roadmap for the current MediaScribe repository.

## Current status

Completed:
- project name and CLI naming are unified around `MediaScribe` / `mediascribe`
- source code is consolidated under the single package `mediascribe/`
- audio, text, and video flows are separated into reusable services
- ASR routing supports local and cloud providers
- default local summary path uses Ollama with `ollama/qwen2.5:3b`
- the default local summary path has been manually verified end to end
- English and Chinese README / quickstart docs are split cleanly
- MIT license and package metadata are in place
- repo cleanup was completed for caches, build leftovers, and generated outputs

## Product shape

MediaScribe is now a focused CLI for:
- audio transcription
- transcript summary
- text summary
- video summary

Core workflow principles:
- transcript first, summary later when useful
- subtitles first for video when available
- local-first defaults, cloud when needed
- simple CLI on top of reusable Python services

## Near-term roadmap

### 1. Stability

- keep the main CLI flows predictable
- preserve and extend automated coverage for audio, text, and video paths
- keep provider routing explicit and easy to debug

### 2. Local-first usability

- make the Ollama summary path feel zero-friction for new users
- keep local hardware guidance practical and visible
- improve environment validation and setup hints

### 3. Documentation polish

- keep `docs/` strictly user-facing
- keep `notes/` for planning and archive material
- keep examples aligned with the current local-default workflow

### 4. Operational ergonomics

- improve provider-specific error messages
- add or refine small doctor / diagnostics commands where they reduce setup friction
- make common Windows workflows especially clear

## Good next candidates

- lightweight environment doctor for summary / ASR prerequisites
- clearer Ollama connection failure messages
- more small end-to-end examples for local summary workflows
- optional benchmark notes for local summary models

## Not a priority right now

- GUI application
- real-time streaming pipeline
- heavy framework abstraction
- broad plugin marketplace expansion
- multi-process orchestration unless a concrete workflow demands it

## Release checklist

Before a release:
- verify README and quickstart in both languages
- verify CLI help text and examples
- run the test suite
- confirm `.gitignore` covers personal local files
- confirm license and package metadata are present
- do one final cleanup pass
