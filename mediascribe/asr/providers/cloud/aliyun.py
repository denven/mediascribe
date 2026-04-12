"""Alibaba Cloud ASR provider for file transcription with speaker diarization."""

import hashlib
import hmac
import logging
import os
import time
import uuid
from base64 import b64encode
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

import requests

from mediascribe.asr.adapters.env import clean_env_value
from mediascribe.asr.config import AliyunASRConfig
from mediascribe.asr.registry import register_asr_provider
from mediascribe.models import TranscribedSegment

logger = logging.getLogger(__name__)

_FILE_TRANS_URL = "https://filetrans.cn-shanghai.aliyuncs.com"
_POLL_INTERVAL = 5


class AliyunASRProvider:
    """Transcribe using Alibaba Cloud Intelligent Speech Interaction (ISI)."""

    def __init__(self, config: AliyunASRConfig) -> None:
        self._access_key_id = config.access_key_id or ""
        self._access_key_secret = config.access_key_secret or ""
        self._appkey = config.appkey or ""
        if config.language and config.language not in ("zh", "zh-CN"):
            logger.warning(
                "[Aliyun] Language '%s' specified, but Aliyun primarily supports Chinese. "
                "Non-Chinese audio may have lower accuracy.",
                config.language,
            )
        self._validate_config()

    def _validate_config(self) -> None:
        missing = []
        if not self._access_key_id:
            missing.append("ALIYUN_ACCESS_KEY_ID")
        if not self._access_key_secret:
            missing.append("ALIYUN_ACCESS_KEY_SECRET")
        if not self._appkey:
            missing.append("ALIYUN_APPKEY")
        if missing:
            raise EnvironmentError(
                f"Missing environment variables: {', '.join(missing)}\n"
                "Get them from Alibaba Cloud Console -> AccessKey Management / Speech Service."
            )

    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        logger.info("[Aliyun] Transcribing: %s", audio_path.name)
        task_id = self._submit_task(audio_path)
        logger.info("[Aliyun] Task submitted: %s", task_id)
        result = self._poll_result(task_id)
        return self._parse_result(result)

    def _submit_task(self, audio_path: Path) -> str:
        ext = audio_path.suffix.lower().lstrip(".")
        format_map = {
            "mp3": "mp3",
            "wav": "pcm",
            "m4a": "mp3",
            "flac": "flac",
            "ogg": "ogg",
            "webm": "opus",
        }
        audio_format = format_map.get(ext, "mp3")

        url = f"{_FILE_TRANS_URL}/api/v1/asr"
        headers = self._build_auth_headers("POST", url)
        headers["Content-Type"] = "application/json"

        body = {
            "appkey": self._appkey,
            "input": {
                "file_url": self._upload_audio(audio_path),
                "source_rate": 16000,
                "format": audio_format,
            },
            "parameters": {
                "diarization": {"enabled": True},
            },
        }

        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        task_id = data.get("data", {}).get("task_id", "")
        if not task_id:
            raise RuntimeError(f"[Aliyun] Failed to submit task: {data}")
        return task_id

    def _upload_audio(self, audio_path: Path) -> str:
        raise NotImplementedError(
            "[Aliyun] Local file upload requires Alibaba Cloud OSS configuration.\n"
            "Please upload your audio to OSS and provide the URL, or set up OSS credentials.\n"
            "See: https://help.aliyun.com/document_detail/90727.html"
        )

    def _poll_result(self, task_id: str) -> dict:
        url = f"{_FILE_TRANS_URL}/api/v1/asr/{task_id}"

        for _ in range(360):
            headers = self._build_auth_headers("GET", url)
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            status = data.get("data", {}).get("task_status", "")
            if status == "SUCCEEDED":
                logger.info("[Aliyun] Transcription completed")
                return data
            if status == "FAILED":
                raise RuntimeError(f"[Aliyun] Transcription failed: {data}")

            logger.debug("[Aliyun] Task status: %s, waiting...", status)
            time.sleep(_POLL_INTERVAL)

        raise RuntimeError("[Aliyun] Transcription timed out after 30 minutes")

    def _build_auth_headers(self, method: str, url: str) -> dict[str, str]:
        nonce = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "AccessKeyId": self._access_key_id,
            "SignatureMethod": "HMAC-SHA1",
            "SignatureVersion": "1.0",
            "SignatureNonce": nonce,
            "Timestamp": timestamp,
        }

        sorted_params = "&".join(
            f"{quote_plus(key)}={quote_plus(value)}" for key, value in sorted(params.items())
        )
        string_to_sign = f"{method}&{quote_plus('/')}&{quote_plus(sorted_params)}"

        sign_key = (self._access_key_secret + "&").encode("utf-8")
        signature = b64encode(
            hmac.new(sign_key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
        ).decode("utf-8")

        params["Signature"] = signature

        return {
            "Authorization": f"Bearer {self._access_key_id}",
            **{f"x-nls-{key.lower()}": value for key, value in params.items()},
        }

    @staticmethod
    def _parse_result(data: dict) -> list[TranscribedSegment]:
        segments: list[TranscribedSegment] = []
        speaker_map: dict[str, str] = {}
        sentences = data.get("data", {}).get("result", {}).get("sentences", [])

        for sentence in sentences:
            speaker_id = str(sentence.get("speaker_id", "0"))
            if speaker_id not in speaker_map:
                speaker_map[speaker_id] = f"Speaker {len(speaker_map) + 1}"

            start = sentence.get("begin_time", 0) / 1000.0
            end = sentence.get("end_time", 0) / 1000.0
            text = sentence.get("text", "").strip()

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


def resolve_aliyun_asr_config(
    *,
    model_size: str | None = None,
    language: str | None = None,
    env: dict[str, str] | None = None,
) -> AliyunASRConfig:
    del model_size
    env_map = env if env is not None else os.environ
    return AliyunASRConfig(
        access_key_id=clean_env_value(env_map.get("ALIYUN_ACCESS_KEY_ID")),
        access_key_secret=clean_env_value(env_map.get("ALIYUN_ACCESS_KEY_SECRET")),
        appkey=clean_env_value(env_map.get("ALIYUN_APPKEY")),
        language=language,
    )


register_asr_provider(
    "aliyun",
    AliyunASRProvider,
    config_resolver=resolve_aliyun_asr_config,
)
