"""Format aligned segments into readable transcript text and write to files."""

import logging
from datetime import datetime
from pathlib import Path

from mediascribe.config import TRANSCRIPTS_SUBDIR
from mediascribe.models import TranscribedSegment

logger = logging.getLogger(__name__)


def format_timestamp(seconds: float) -> str:
    """Convert seconds to [HH:MM:SS] format."""
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"[{h:02d}:{m:02d}:{s:02d}]"


def apply_speaker_names(
    segments: list[TranscribedSegment],
    speaker_names: list[str] | None = None,
) -> list[TranscribedSegment]:
    """Replace default speaker labels with user-provided names by first appearance order."""
    if not speaker_names:
        return segments

    cleaned_names = [name.strip() for name in speaker_names if name.strip()]
    if not cleaned_names:
        return segments

    label_map: dict[str, str] = {}
    next_name_index = 0
    renamed_segments: list[TranscribedSegment] = []

    for seg in segments:
        if seg.speaker.startswith("Speaker ") and seg.speaker not in label_map:
            if next_name_index < len(cleaned_names):
                label_map[seg.speaker] = cleaned_names[next_name_index]
                next_name_index += 1

        renamed_segments.append(
            TranscribedSegment(
                start=seg.start,
                end=seg.end,
                speaker=label_map.get(seg.speaker, seg.speaker),
                text=seg.text,
            )
        )

    return renamed_segments


def format_transcript(
    segments: list[TranscribedSegment],
    source_filename: str,
) -> str:
    """Format aligned segments into a readable transcript string.

    Args:
        segments: Aligned segments with speaker labels and timestamps.
        source_filename: Original audio filename for the header.

    Returns:
        Formatted transcript text.
    """
    lines = [
        f"=== {source_filename} ===",
        f"Transcribed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for seg in segments:
        timestamp = format_timestamp(seg.start)
        lines.append(f"{timestamp} {seg.speaker}: {seg.text}")

    return "\n".join(lines) + "\n"


def write_transcript(
    transcript_text: str,
    source_filename: str,
    output_dir: Path,
) -> Path:
    """Write transcript text to a file in the output directory.

    Args:
        transcript_text: Formatted transcript content.
        source_filename: Original audio filename (used to derive output name).
        output_dir: Base output directory.

    Returns:
        Path to the written transcript file.
    """
    transcripts_dir = output_dir / TRANSCRIPTS_SUBDIR
    transcripts_dir.mkdir(parents=True, exist_ok=True)

    stem = Path(source_filename).stem
    output_path = transcripts_dir / f"{stem}.txt"

    output_path.write_text(transcript_text, encoding="utf-8")
    logger.info("Transcript written: %s", output_path)

    return output_path
