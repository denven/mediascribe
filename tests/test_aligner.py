"""Tests for the local ASR provider alignment logic."""

from mediascribe.asr.local import LocalASRProvider, _RawTranscript, _SpeakerTurn
from mediascribe.models import TranscribedSegment


def test_align_basic() -> None:
    transcripts = [
        _RawTranscript(start=0.0, end=3.0, text="Hello everyone"),
        _RawTranscript(start=3.5, end=6.0, text="Let's start"),
    ]
    speakers = [
        _SpeakerTurn(start=0.0, end=3.2, speaker="SPEAKER_00"),
        _SpeakerTurn(start=3.3, end=6.5, speaker="SPEAKER_01"),
    ]

    result = LocalASRProvider._align(transcripts, speakers)

    assert len(result) == 2
    assert result[0].speaker == "Speaker 1"
    assert result[0].text == "Hello everyone"
    assert result[1].speaker == "Speaker 2"
    assert result[1].text == "Let's start"


def test_align_empty_transcripts() -> None:
    speakers = [_SpeakerTurn(start=0.0, end=5.0, speaker="SPEAKER_00")]
    result = LocalASRProvider._align([], speakers)
    assert result == []


def test_align_empty_speakers() -> None:
    transcripts = [
        _RawTranscript(start=0.0, end=3.0, text="Hello"),
        _RawTranscript(start=4.0, end=7.0, text="World"),
    ]
    result = LocalASRProvider._align(transcripts, [])
    assert len(result) == 2
    assert all(seg.speaker == "Speaker 1" for seg in result)


def test_align_no_overlap() -> None:
    transcripts = [_RawTranscript(start=10.0, end=12.0, text="Late segment")]
    speakers = [_SpeakerTurn(start=0.0, end=5.0, speaker="SPEAKER_00")]
    result = LocalASRProvider._align(transcripts, speakers)
    assert result[0].speaker == "Unknown"


def test_align_speaker_ordering() -> None:
    """Speakers are numbered by first appearance in timeline."""
    transcripts = [
        _RawTranscript(start=0.0, end=2.0, text="A"),
        _RawTranscript(start=3.0, end=5.0, text="B"),
        _RawTranscript(start=6.0, end=8.0, text="C"),
    ]
    speakers = [
        _SpeakerTurn(start=0.0, end=2.5, speaker="SPEAKER_02"),
        _SpeakerTurn(start=2.5, end=5.5, speaker="SPEAKER_00"),
        _SpeakerTurn(start=5.5, end=8.5, speaker="SPEAKER_02"),
    ]
    result = LocalASRProvider._align(transcripts, speakers)
    assert result[0].speaker == "Speaker 1"  # SPEAKER_02 appears first
    assert result[1].speaker == "Speaker 2"  # SPEAKER_00 appears second
    assert result[2].speaker == "Speaker 1"  # SPEAKER_02 again


def test_align_overlapping_speakers() -> None:
    """Transcript segment overlapping two speakers picks the one with more overlap."""
    transcripts = [_RawTranscript(start=2.0, end=6.0, text="Overlap test")]
    speakers = [
        _SpeakerTurn(start=0.0, end=3.0, speaker="SPEAKER_00"),  # 1s overlap
        _SpeakerTurn(start=3.0, end=8.0, speaker="SPEAKER_01"),  # 3s overlap
    ]
    result = LocalASRProvider._align(transcripts, speakers)
    assert result[0].speaker == "Speaker 2"  # SPEAKER_01 has more overlap
