"""Shortcut module for the local ASR provider."""

from mediascribe.asr.providers.local import LocalASRProvider, _RawTranscript, _SpeakerTurn

__all__ = ["LocalASRProvider", "_RawTranscript", "_SpeakerTurn"]
