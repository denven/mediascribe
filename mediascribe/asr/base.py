"""ASR provider base protocol."""

from pathlib import Path
from typing import Protocol

from mediascribe.models import TranscribedSegment


class ASRProvider(Protocol):
    """Unified interface for all ASR providers (local and cloud).

    Each provider takes an audio file and returns transcribed segments
    with speaker labels and timestamps.
    """

    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        """Transcribe an audio file with speaker diarization.

        Args:
            audio_path: Path to the audio file.

        Returns:
            List of TranscribedSegment sorted by start time.
        """
        ...
