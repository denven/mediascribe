# Changelog

All notable changes to MediaScribe are documented in this file.

The project follows a simple Keep a Changelog-style structure for human-readable release notes.

## [0.1.1] - 2026-04-16

Patch release focused on reliability, logging clarity, and provider configuration fixes after the initial GitHub release.

### Added

- Runtime log filtering tests covering LiteLLM noise suppression and third-party debug toggle behavior
- Summary pipeline debug markers that make it easier to tell when the LLM call starts, returns, and writes the output file
- Additional summary runtime tests that protect local-vs-cloud API base selection behavior

### Changed

- Azure locale UX now consistently points users to full BCP-47 locales such as `zh-CN` and `en-US`
- Azure invalid-locale failures now surface a clearer remediation hint with the official Azure Speech language support reference
- Verbose mode now focuses on MediaScribe debug logs while keeping raw `openai` / `httpcore` / `LiteLLM` traces hidden by default
- Added opt-in `MEDIASCRIBE_DEBUG_THIRD_PARTY=1` support for low-level provider debugging when needed
- `MEDIASCRIBE_LLM_API_BASE` now auto-applies only to local `ollama/...` models instead of leaking into cloud models like `gpt-5-mini`
- README and quick-start docs now explain Azure locale requirements, local-vs-cloud summary endpoint behavior, and the new verbose logging behavior
- CI setup was refined after `v0.1.0`, including workflow fixes and explicit `ffmpeg` installation
- Social preview artwork and repo presentation details were polished

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
- GitHub Actions CI workflow for `ruff` linting and `pytest` test runs
- Social preview artwork under `assets/social-preview.png` for repository and release presentation

### Changed

- Default summary path is documented as local Ollama with `ollama/qwen2.5:3b`
- Runtime hints now explain that local ASR uses more hardware resources
- Runtime hints now clarify that cloud summary generation may incur LLM API cost
- README was rewritten for GitHub presentation with clearer workflow guidance and release-oriented docs links
- README badges now expose GitHub release and CI status
- `.gitignore` now covers local environments, outputs, caches, cookies, and temp artifacts
- Added a manual integration-check script for the default local summary path

### Notes

- `--asr local` typically uses much more local CPU / GPU / RAM than cloud ASR
- Cloud ASR can reduce local hardware pressure, but may introduce provider cost
- The default local summary path (`ollama/qwen2.5:3b`) has been manually verified end to end
