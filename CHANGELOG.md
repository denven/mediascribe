# Changelog

All notable changes to MediaScribe are documented in this file.

The project follows a simple Keep a Changelog-style structure for human-readable release notes.

## [0.1.0] - 2026-04-12

Initial GitHub-ready MediaScribe release.

### Added

- Project-facing MediaScribe branding with new CLI entry points:
  - `mediascribe`
  - `mediascribe-transcriber`
  - `mediascribe-text`
- Standalone transcription service that can be reused by other Python scripts
- Standalone text / transcript summary service reusable outside the one-shot audio flow
- Video summary flow with subtitle-first processing, ASR fallback, and audio-only extraction
- Remote video authentication helpers with cookie file, site-specific cookie map, and browser-cookie fallback support
- `doctor-video-auth` command for inspecting video auth resolution behavior
- Azure long-audio auto-splitting for large or long inputs before fast transcription upload
- Bilingual documentation set covering quick start, architecture, ASR, summary, plugin providers, and benchmark notes
- Performance reference notes from practical end-to-end runs

### Changed

- Default summary path is documented as local Ollama with `ollama/qwen2.5:3b`
- Runtime hints now explain that local ASR uses more hardware resources
- Runtime hints now clarify that cloud summary generation may incur LLM API cost
- README was rewritten for GitHub presentation with clearer workflow guidance and release-oriented docs links
- `.gitignore` now covers local environments, outputs, caches, cookies, and temp artifacts
- Added a manual integration-check script for the default local summary path

### Notes

- `--asr local` typically uses much more local CPU / GPU / RAM than cloud ASR
- Cloud ASR can reduce local hardware pressure, but may introduce provider cost
- The default local summary path (`ollama/qwen2.5:3b`) has been manually verified end to end
