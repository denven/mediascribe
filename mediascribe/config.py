"""Centralized configuration defaults."""

SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
SUPPORTED_SUBTITLE_EXTENSIONS = {".srt", ".vtt", ".ass", ".ssa", ".txt", ".md"}
SUPPORTED_TRANSCRIPT_EXTENSIONS = {".txt", ".md"}

DEFAULT_WHISPER_MODEL = "medium"
DEFAULT_LLM_MODEL = "ollama/qwen2.5:3b"
DEFAULT_LLM_API_BASE = "http://localhost:11434"
DEFAULT_LLM_MODELS_BY_ENV = {
    "ANTHROPIC_API_KEY": "claude-sonnet-4-20250514",
    "OPENAI_API_KEY": "gpt-5.4-mini",
    "GEMINI_API_KEY": "gemini/gemini-2.0-flash",
    "DEEPSEEK_API_KEY": "deepseek/deepseek-chat",
}
DEFAULT_ASR_PROVIDER = "local"
DEFAULT_OUTPUT_DIR = "./output"
TRANSCRIPTS_SUBDIR = "transcripts"
SUBTITLES_SUBDIR = "subtitles"
MEDIA_SUBDIR = "media"
SUMMARY_FILENAME = "summary.md"

SUMMARY_SYSTEM_PROMPT = """You are an expert meeting summarizer. Given the transcript of one or more audio recordings, produce a structured Markdown summary.

Your summary MUST include these sections:
## Key Points
## Discussion Topics
## Action Items
## Decisions Made

Guidelines:
- Write in the same language as the transcript.
- Be concise but capture all important information.
- For Action Items, use checkbox format: - [ ] ...
- If multiple audio files are included, organize topics across all of them cohesively.
- Do NOT invent information not present in the transcript."""

SUMMARY_USER_PROMPT_TEMPLATE = """Please summarize the following transcript(s):

{transcripts}"""
