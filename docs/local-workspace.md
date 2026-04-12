# Local Workspace

Language: **English** | [Chinese](local-workspace.zh-CN.md)

This note describes a simple local working layout for files that are useful during day-to-day MediaScribe use but are not part of the package itself.

## Recommended folders

### `audios/`

Use this as a convenient local drop folder for:
- raw meeting recordings
- interview audio
- sample media for manual testing
- hand-written notes or summaries you want to keep beside the source media

Typical layout:

```text
audios/
  meeting-01.wav
  interview-a.m4a
  transcripts/
  summary.md
```

Notes:
- this folder is for local working material, not Python package code
- generated `transcripts/` and `summary.md` can live here if you like a self-contained workflow
- if you prefer a cleaner separation, write outputs to a dedicated `output/` directory instead

### `cookies/`

Use this only for local yt-dlp authentication files:
- site-specific cookie exports
- browser-derived cookie files
- temporary auth files for private or rate-limited video sources

Typical layout:

```text
cookies/
  global.txt
  bilibili.txt
```

Notes:
- treat everything under `cookies/` as secret
- do not commit real cookie files
- MediaScribe examples often reference this folder in `YTDLP_COOKIES_FILE` and `YTDLP_SITE_COOKIE_MAP`

## Generated folders

These are normal temporary or generated working folders:
- `output/`
- `output_*`
- `transcripts/`
- `subtitles/`
- `media/`

They are ignored by `.gitignore`, so you can keep local runs without cluttering the repository.

## Suggested habits

- keep source media under `audios/`
- keep authentication material under `cookies/`
- keep user-facing docs under `docs/`
- keep internal planning or archive material under `notes/`
- keep generated outputs disposable unless they are intentional examples
