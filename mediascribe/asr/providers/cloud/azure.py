"""Azure Speech Service ASR provider for fast transcription with diarization."""

import json
import logging
import mimetypes
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

import requests

from mediascribe.asr.adapters.env import clean_env_value
from mediascribe.asr.config import AzureASRConfig
from mediascribe.asr.registry import register_asr_provider
from mediascribe.ffmpeg_utils import (
    convert_audio_to_pcm_wav,
    inspect_audio_media,
    split_audio_to_pcm_wav_chunks,
)
from mediascribe.models import TranscribedSegment

logger = logging.getLogger(__name__)

_API_VERSION = "2024-11-15"
_DIRECT_UPLOAD_SUFFIXES = {".wav"}
_DECODE_ERROR_MARKERS = (
    "audio stream could not be decoded",
    "could not be decoded with the provided configuration",
)
_AUTO_SPLIT_DURATION_SECONDS = 60 * 60
_AUTO_SPLIT_SIZE_BYTES = 150 * 1024 * 1024
_AUTO_SPLIT_CHUNK_SECONDS = 30 * 60


class AzureASRProvider:
    """Transcribe using Azure Cognitive Services Speech-to-Text."""

    def __init__(self, config: AzureASRConfig) -> None:
        self._key = (config.key or "").strip()
        self._region = (config.region or "").strip()
        self._endpoint = self._resolve_endpoint(config.endpoint, self._region)
        self._language = config.language
        self._validate_config()

    def _validate_config(self) -> None:
        if not self._key:
            raise EnvironmentError(
                "AZURE_SPEECH_KEY environment variable is required.\n"
                "Get it from Azure Portal -> Speech resource -> Keys and Endpoint."
            )
        if not self._endpoint:
            raise EnvironmentError(
                "Azure Speech endpoint configuration is required.\n"
                "Set AZURE_SPEECH_REGION=eastus or "
                "AZURE_SPEECH_ENDPOINT=https://<resource>.cognitiveservices.azure.com"
            )

    @staticmethod
    def _resolve_endpoint(custom_endpoint: str | None, region: str) -> str:
        endpoint = (custom_endpoint or "").strip()
        if endpoint:
            return endpoint.rstrip("/")
        if not region:
            return ""
        return f"https://{region}.api.cognitive.microsoft.com"

    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        logger.info("[Azure] Transcribing: %s", audio_path.name)
        return self._transcribe_realtime(audio_path)

    def _transcribe_realtime(self, audio_path: Path) -> list[TranscribedSegment]:
        url = f"{self._endpoint}/speechtotext/transcriptions:transcribe?api-version={_API_VERSION}"
        definition = self._build_definition()

        with self._prepare_audio_upload(audio_path, force_normalize=False) as upload_path:
            if self._should_auto_split(upload_path):
                return self._transcribe_in_chunks(url, definition, upload_path)

            try:
                resp = self._submit_prepared_realtime_request(url, definition, upload_path)
            except requests.HTTPError as exc:
                if self._should_retry_with_normalized_audio(audio_path, exc.response):
                    logger.info(
                        "[Azure] Retrying %s with local PCM WAV normalization after decode failure",
                        audio_path.name,
                    )
                    with self._prepare_audio_upload(audio_path, force_normalize=True) as normalized_path:
                        if self._should_auto_split(normalized_path):
                            return self._transcribe_in_chunks(url, definition, normalized_path)
                        resp = self._submit_prepared_realtime_request(url, definition, normalized_path)
                else:
                    raise

        return self._parse_result(resp.json())

    def _submit_prepared_realtime_request(
        self,
        url: str,
        definition: dict,
        upload_path: Path,
    ) -> requests.Response:
        audio_data = upload_path.read_bytes()
        audio_content_type = mimetypes.guess_type(upload_path.name)[0] or "application/octet-stream"

        resp = requests.post(
            url,
            headers={"Ocp-Apim-Subscription-Key": self._key},
            files={
                "audio": (upload_path.name, audio_data, audio_content_type),
                "definition": (None, json.dumps(definition), "application/json"),
            },
            timeout=300,
        )

        try:
            resp.raise_for_status()
        except requests.HTTPError as exc:
            detail = self._extract_error_detail(resp)
            if detail:
                raise requests.HTTPError(
                    f"{exc}. Azure details: {detail}",
                    response=resp,
                    request=resp.request,
                ) from exc
            raise

        return resp

    def _should_auto_split(self, upload_path: Path) -> bool:
        info = inspect_audio_media(upload_path)
        reasons: list[str] = []

        if info.duration_seconds is not None and info.duration_seconds > _AUTO_SPLIT_DURATION_SECONDS:
            reasons.append(
                f"duration {info.duration_seconds:.0f}s exceeds {_AUTO_SPLIT_DURATION_SECONDS:.0f}s"
            )
        if info.size_bytes > _AUTO_SPLIT_SIZE_BYTES:
            reasons.append(f"size {info.size_bytes} bytes exceeds {_AUTO_SPLIT_SIZE_BYTES} bytes")

        if reasons:
            logger.info(
                "[Azure] Auto-splitting %s into %d-minute chunks because %s",
                upload_path.name,
                _AUTO_SPLIT_CHUNK_SECONDS // 60,
                "; ".join(reasons),
            )
            return True
        return False

    def _transcribe_in_chunks(self, url: str, definition: dict, upload_path: Path) -> list[TranscribedSegment]:
        with tempfile.TemporaryDirectory(prefix="azure-asr-split-") as tmp_dir:
            chunk_paths = split_audio_to_pcm_wav_chunks(
                upload_path,
                Path(tmp_dir),
                chunk_seconds=_AUTO_SPLIT_CHUNK_SECONDS,
            )

            all_segments: list[TranscribedSegment] = []
            chunk_offset = 0.0
            total_chunks = len(chunk_paths)

            for index, chunk_path in enumerate(chunk_paths, start=1):
                logger.info("[Azure] Transcribing chunk %d/%d: %s", index, total_chunks, chunk_path.name)
                resp = self._submit_prepared_realtime_request(url, definition, chunk_path)
                chunk_segments = self._parse_result(resp.json())
                all_segments.extend(self._offset_segments(chunk_segments, chunk_offset))
                chunk_info = inspect_audio_media(chunk_path)
                chunk_offset += chunk_info.duration_seconds or _AUTO_SPLIT_CHUNK_SECONDS

            return all_segments

    @contextmanager
    def _prepare_audio_upload(self, audio_path: Path, *, force_normalize: bool):
        if not force_normalize and audio_path.suffix.lower() in _DIRECT_UPLOAD_SUFFIXES:
            yield audio_path
            return

        with tempfile.TemporaryDirectory(prefix="azure-asr-") as tmp_dir:
            normalized_path = Path(tmp_dir) / f"{audio_path.stem}.azure.wav"
            logger.info(
                "[Azure] Normalizing %s to mono 16k PCM WAV before upload",
                audio_path.name,
            )
            convert_audio_to_pcm_wav(audio_path, normalized_path)
            yield normalized_path

    @staticmethod
    def _should_retry_with_normalized_audio(
        audio_path: Path,
        response: requests.Response | None,
    ) -> bool:
        if audio_path.suffix.lower() not in _DIRECT_UPLOAD_SUFFIXES or response is None:
            return False

        detail = AzureASRProvider._extract_error_detail(response).lower()
        return any(marker in detail for marker in _DECODE_ERROR_MARKERS)

    def _build_definition(self) -> dict:
        definition: dict = {
            "diarization": {
                "enabled": True,
                "maxSpeakers": 10,
            },
        }

        if self._language:
            definition["locales"] = [self._language]
        else:
            definition["locales"] = [
                "zh-CN",
                "en-US",
                "ja-JP",
                "ko-KR",
                "zh-TW",
                "en-GB",
                "fr-FR",
                "de-DE",
                "es-ES",
            ]
            logger.info("[Azure] No language specified, using auto language identification")

        return definition

    @staticmethod
    def _extract_error_detail(resp: requests.Response) -> str:
        try:
            payload = resp.json()
        except ValueError:
            return resp.text.strip()

        for key in ("message", "error", "details"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = value.get("message") or value.get("code")
                if isinstance(nested, str) and nested.strip():
                    return nested.strip()

        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _parse_result(result: dict) -> list[TranscribedSegment]:
        segments: list[TranscribedSegment] = []
        speaker_map: dict[int, str] = {}

        for phrase in result.get("phrases", []):
            speaker_id = phrase.get("speaker", 0)
            if speaker_id not in speaker_map:
                speaker_map[speaker_id] = f"Speaker {len(speaker_map) + 1}"

            start = phrase.get("offsetMilliseconds", 0) / 1000.0
            end = start + (phrase.get("durationMilliseconds", 0) / 1000.0)
            text = phrase.get("text", "").strip()

            if text:
                segments.append(
                    TranscribedSegment(
                        start=start,
                        end=end,
                        speaker=speaker_map[speaker_id],
                        text=text,
                    )
                )

        return segments

    @staticmethod
    def _offset_segments(
        segments: list[TranscribedSegment],
        offset_seconds: float,
    ) -> list[TranscribedSegment]:
        if offset_seconds <= 0:
            return segments

        return [
            TranscribedSegment(
                start=segment.start + offset_seconds,
                end=segment.end + offset_seconds,
                speaker=segment.speaker,
                text=segment.text,
            )
            for segment in segments
        ]


def resolve_azure_asr_config(
    *,
    model_size: str | None = None,
    language: str | None = None,
    env: dict[str, str] | None = None,
) -> AzureASRConfig:
    del model_size
    env_map = env if env is not None else os.environ
    return AzureASRConfig(
        key=clean_env_value(env_map.get("AZURE_SPEECH_KEY")),
        region=clean_env_value(env_map.get("AZURE_SPEECH_REGION")),
        endpoint=clean_env_value(env_map.get("AZURE_SPEECH_ENDPOINT")),
        language=language,
    )


register_asr_provider(
    "azure",
    AzureASRProvider,
    config_resolver=resolve_azure_asr_config,
)
