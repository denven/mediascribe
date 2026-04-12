# Benchmark Notes

This document records practical end-to-end timing references gathered during real runs on the current machine and network environment.

## Scope

- These are workflow timings, not isolated model-only timings.
- Each elapsed time may include:
  - remote download
  - local audio extraction
  - subtitle fetch / conversion
  - transcription
  - summary generation
  - file write
- Treat these as reference points for comparison, not strict guarantees.

## 2026-04-05 Video Summary Runs

Environment used in these runs:

- `ffmpeg`
- `yt-dlp`
- Azure ASR
- a cloud summary model

| Scenario | Input Duration | Method | End-to-End Time | Approx Speed |
| --- | ---: | --- | ---: | ---: |
| Local MP4 `cleaned_...mp4` | 6m06s | `audio_asr` (local video -> extract audio -> Azure ASR -> cloud summary) | 1m41s | about 3.6x realtime |
| YouTube `3DlXq9nsQOE` | 18m30s | `audio_asr` (remote video -> download audio -> Azure ASR -> cloud summary) | 2m26s | about 7.6x realtime |
| YouTube `aircAruvnKk` (with subtitles) | 18m26s | `subtitles` (remote video -> subtitles directly -> cloud summary) | 31s | about 35.9x realtime |
| Facebook `1ahSKdqfDU` | 19s | `audio_asr` (remote video -> download audio -> Azure ASR -> cloud summary) | 36s | about 0.5x realtime |
| Bilibili `BV1VtcYzTEZn` (no cookies) | 2m59s | `audio_asr` (subtitle fail -> audio fallback -> Azure ASR -> cloud summary) | 58s | about 3.1x realtime |
| Bilibili `BV1VtcYzTEZn` (browser cookie failure then fallback) | 2m59s | `audio_asr` (browser cookies fail -> unauthenticated fallback -> download audio -> Azure ASR -> cloud summary) | 1m04s | about 2.8x realtime |

## Qualitative Observations

- Subtitle-first summary is by far the fastest path for long videos.
- For short clips, fixed startup overhead dominates total time.
- In the current environment, local `--asr local` is much slower than Azure for video workflows.
- A previous local-ASR run on a ~6 minute local video did not finish within 15 minutes.

## Suggested Future Logging Format

When adding future benchmark entries, keep these fields:

- date
- source type
- input duration
- method / path used
- end-to-end elapsed time
- notes about failures / fallback behavior
