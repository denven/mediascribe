"""Local ASR provider: faster-whisper + pyannote.audio."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from mediascribe.asr.adapters.env import clean_env_value
from mediascribe.asr.config import LocalASRConfig
from mediascribe.asr.registry import register_asr_provider
from mediascribe.config import DEFAULT_WHISPER_MODEL
from mediascribe.models import TranscribedSegment

logger = logging.getLogger(__name__)

try:
    from faster_whisper import WhisperModel
    from pyannote.audio import Pipeline

    _LOCAL_DEPS_AVAILABLE = True
except ImportError:
    _LOCAL_DEPS_AVAILABLE = False

_INSTALL_HINT = (
    "Local ASR dependencies are not installed.\n"
    "Install with:  pip install -r requirements-local.txt\n"
    '    or:        pip install ".[local]"\n'
    "Alternatively, use cloud ASR:  --asr azure / aliyun / iflytek"
)


@dataclass
class _RawTranscript:
    start: float
    end: float
    text: str


@dataclass
class _SpeakerTurn:
    start: float
    end: float
    speaker: str


class LocalASRProvider:
    """Transcribe locally using faster-whisper + pyannote speaker diarization."""

    def __init__(
        self,
        config: LocalASRConfig,
    ) -> None:
        if not _LOCAL_DEPS_AVAILABLE:
            raise EnvironmentError(_INSTALL_HINT)
        self._model_size = config.model_size or DEFAULT_WHISPER_MODEL
        self._language = config.language
        self._hf_token = config.hf_token
        self._whisper: WhisperModel | None = None
        self._diarize_pipeline: Pipeline | None = None

    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        raw = self._transcribe_whisper(audio_path)
        speakers = self._diarize(audio_path)
        return self._align(raw, speakers)

    def _get_whisper(self) -> WhisperModel:
        if self._whisper is None:
            logger.info("Loading Whisper model: %s", self._model_size)
            self._whisper = WhisperModel(self._model_size, device="auto", compute_type="auto")
        return self._whisper

    def _transcribe_whisper(self, audio_path: Path) -> list[_RawTranscript]:
        logger.info(
            "Transcribing: %s (model=%s, language=%s)",
            audio_path.name,
            self._model_size,
            self._language or "auto",
        )

        model = self._get_whisper()
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=self._language,
            vad_filter=True,
            word_timestamps=False,
        )
        logger.info("Detected language: %s (probability: %.2f)", info.language, info.language_probability)

        segments = [
            _RawTranscript(start=seg.start, end=seg.end, text=seg.text.strip())
            for seg in segments_iter
            if seg.text.strip()
        ]
        logger.info("Transcribed %d segments from %s", len(segments), audio_path.name)
        return segments

    def _get_diarize_pipeline(self) -> Pipeline:
        if self._diarize_pipeline is None:
            if not self._hf_token:
                raise EnvironmentError(
                    "HF_TOKEN environment variable is required for speaker diarization.\n"
                    "Get your token at https://huggingface.co/settings/tokens\n"
                    "Then set: export HF_TOKEN=hf_xxx  (or set HF_TOKEN=hf_xxx on Windows)"
                )
            logger.info("Loading pyannote diarization pipeline...")
            self._diarize_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self._hf_token,
            )
        return self._diarize_pipeline

    def _diarize(self, audio_path: Path) -> list[_SpeakerTurn]:
        try:
            pipeline = self._get_diarize_pipeline()
        except EnvironmentError as e:
            logger.warning("Diarization skipped: %s", e)
            return []

        logger.info("Running speaker diarization on: %s", audio_path.name)
        diarization = pipeline(str(audio_path))

        turns = [
            _SpeakerTurn(start=turn.start, end=turn.end, speaker=speaker)
            for turn, _, speaker in diarization.itertracks(yield_label=True)
        ]
        speakers = {t.speaker for t in turns}
        logger.info("Diarization complete: %d segments, %d speakers", len(turns), len(speakers))
        return turns

    @staticmethod
    def _align(
        transcripts: list[_RawTranscript],
        speakers: list[_SpeakerTurn],
    ) -> list[TranscribedSegment]:
        if not transcripts:
            return []

        if not speakers:
            return [
                TranscribedSegment(start=t.start, end=t.end, speaker="Speaker 1", text=t.text)
                for t in transcripts
            ]

        speaker_map: dict[str, str] = {}
        for turn in speakers:
            if turn.speaker not in speaker_map:
                speaker_map[turn.speaker] = f"Speaker {len(speaker_map) + 1}"

        result = []
        for transcript in transcripts:
            best_speaker_raw = None
            best_overlap = 0.0
            for speaker_turn in speakers:
                overlap = max(
                    0.0,
                    min(transcript.end, speaker_turn.end) - max(transcript.start, speaker_turn.start),
                )
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_speaker_raw = speaker_turn.speaker

            label = speaker_map.get(best_speaker_raw, "Unknown") if best_speaker_raw else "Unknown"
            result.append(
                TranscribedSegment(
                    start=transcript.start,
                    end=transcript.end,
                    speaker=label,
                    text=transcript.text,
                )
            )

        return result


def resolve_local_asr_config(
    *,
    model_size: str = DEFAULT_WHISPER_MODEL,
    language: str | None = None,
    env: dict[str, str] | None = None,
) -> LocalASRConfig:
    env_map = env if env is not None else os.environ
    return LocalASRConfig(
        model_size=model_size,
        language=language,
        hf_token=clean_env_value(env_map.get("HF_TOKEN")),
    )


register_asr_provider(
    "local",
    LocalASRProvider,
    config_resolver=resolve_local_asr_config,
)
