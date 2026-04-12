"""iFlytek ASR provider for file transcription with speaker diarization."""

import base64
import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path

import requests

from mediascribe.asr.adapters.env import clean_env_value
from mediascribe.asr.config import IflytekASRConfig
from mediascribe.asr.registry import register_asr_provider
from mediascribe.models import TranscribedSegment

logger = logging.getLogger(__name__)

_UPLOAD_URL = "https://raasr.xfyun.cn/v2/api/upload"
_GET_RESULT_URL = "https://raasr.xfyun.cn/v2/api/getResult"
_POLL_INTERVAL = 5


class IflytekASRProvider:
    """Transcribe using iFlytek Speech-to-Text with speaker diarization."""

    def __init__(self, config: IflytekASRConfig) -> None:
        self._app_id = config.app_id or ""
        self._api_key = config.api_key or ""
        if config.language and config.language not in ("zh", "zh-CN"):
            logger.warning(
                "[iFlytek] Language '%s' specified, but iFlytek primarily supports Chinese. "
                "Non-Chinese audio may have lower accuracy.",
                config.language,
            )
        self._validate_config()

    def _validate_config(self) -> None:
        missing = []
        if not self._app_id:
            missing.append("IFLYTEK_APP_ID")
        if not self._api_key:
            missing.append("IFLYTEK_API_KEY")
        if missing:
            raise EnvironmentError(
                f"Missing environment variables: {', '.join(missing)}\n"
                "Get them from iFlytek Console: https://console.xfyun.cn/services/lfasr"
            )

    def _build_signature(self, ts: str) -> str:
        base_string = self._app_id + ts
        md5_hash = hashlib.md5(base_string.encode("utf-8")).hexdigest()
        signature = hmac.new(
            self._api_key.encode("utf-8"),
            md5_hash.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def _auth_params(self) -> dict[str, str]:
        ts = str(int(time.time()))
        return {
            "appId": self._app_id,
            "ts": ts,
            "signa": self._build_signature(ts),
        }

    def transcribe(self, audio_path: Path) -> list[TranscribedSegment]:
        logger.info("[iFlytek] Transcribing: %s", audio_path.name)
        task_id = self._upload(audio_path)
        logger.info("[iFlytek] Task created: %s", task_id)
        result = self._poll_result(task_id)
        return self._parse_result(result)

    def _upload(self, audio_path: Path) -> str:
        file_size = audio_path.stat().st_size
        audio_data = audio_path.read_bytes()

        params = self._auth_params()
        params.update(
            {
                "fileName": audio_path.name,
                "fileSize": str(file_size),
                "duration": "",
                "roleType": "2",
            }
        )

        resp = requests.post(
            _UPLOAD_URL,
            headers={"Content-Type": "application/json"},
            params=params,
            data=audio_data,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != "000000":
            raise RuntimeError(f"[iFlytek] Upload failed: {data.get('descInfo', data)}")

        content = data.get("content", {})
        if isinstance(content, str):
            content = json.loads(content)

        task_id = content.get("orderId", "")
        if not task_id:
            raise RuntimeError(f"[iFlytek] No task ID in response: {data}")
        return task_id

    def _poll_result(self, task_id: str) -> dict:
        for _ in range(360):
            params = self._auth_params()
            params["orderId"] = task_id

            resp = requests.post(
                _GET_RESULT_URL,
                headers={"Content-Type": "application/json"},
                params=params,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "000000":
                raise RuntimeError(f"[iFlytek] Query failed: {data.get('descInfo', data)}")

            content = data.get("content", {})
            if isinstance(content, str):
                content = json.loads(content)

            status = content.get("orderInfo", {}).get("status")
            if status == 4:
                logger.info("[iFlytek] Transcription completed")
                return content
            if status == -1:
                raise RuntimeError(f"[iFlytek] Transcription failed: {content}")

            logger.debug("[iFlytek] Task status: %s, waiting...", status)
            time.sleep(_POLL_INTERVAL)

        raise RuntimeError("[iFlytek] Transcription timed out after 30 minutes")

    @staticmethod
    def _parse_result(content: dict) -> list[TranscribedSegment]:
        segments: list[TranscribedSegment] = []
        speaker_map: dict[str, str] = {}

        result_list = content.get("orderResult", "")
        if isinstance(result_list, str):
            try:
                result_list = json.loads(result_list)
            except json.JSONDecodeError:
                logger.error("[iFlytek] Failed to parse orderResult")
                return segments

        lattice_list = result_list if isinstance(result_list, list) else result_list.get("lattice", [])

        for item in lattice_list:
            json_1best = item.get("json_1best", "{}")
            if isinstance(json_1best, str):
                try:
                    json_1best = json.loads(json_1best)
                except json.JSONDecodeError:
                    continue

            st = json_1best.get("st", {})
            speaker_id = str(st.get("rl", "0"))
            if speaker_id not in speaker_map:
                speaker_map[speaker_id] = f"Speaker {len(speaker_map) + 1}"

            words = []
            bg_ms = int(st.get("bg", "0"))
            ed_ms = bg_ms

            for rt in st.get("rt", []):
                for ws in rt.get("ws", []):
                    for cw in ws.get("cw", []):
                        word = cw.get("w", "")
                        if word:
                            words.append(word)
                        wb = int(cw.get("wb", ed_ms))
                        we = int(cw.get("we", wb))
                        if we > ed_ms:
                            ed_ms = we

            text = "".join(words).strip()
            if text:
                segments.append(
                    TranscribedSegment(
                        start=bg_ms / 1000.0,
                        end=ed_ms / 1000.0,
                        speaker=speaker_map[speaker_id],
                        text=text,
                    )
                )

        return segments


def resolve_iflytek_asr_config(
    *,
    model_size: str | None = None,
    language: str | None = None,
    env: dict[str, str] | None = None,
) -> IflytekASRConfig:
    del model_size
    env_map = env if env is not None else os.environ
    return IflytekASRConfig(
        app_id=clean_env_value(env_map.get("IFLYTEK_APP_ID")),
        api_key=clean_env_value(env_map.get("IFLYTEK_API_KEY")),
        language=language,
    )


register_asr_provider(
    "iflytek",
    IflytekASRProvider,
    config_resolver=resolve_iflytek_asr_config,
)
