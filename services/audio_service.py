import logging
import subprocess
from datetime import datetime
from pathlib import Path

import requests

from config import TTS_URL, TTS_TRAIN_DIR, UPLOAD_DIR


logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self, request_timeout=(5, 120)):
        self.request_timeout = request_timeout

    @staticmethod
    def _safe_user_output_dir(username: str) -> Path:
        if not username:
            raise ValueError("Username is required")

        upload_root = Path(UPLOAD_DIR).resolve()
        user_dir = (upload_root / username).resolve()
        if user_dir.parent != upload_root:
            raise ValueError("Unsafe username path")
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    @staticmethod
    def _require_training_result(payload) -> dict:
        if not isinstance(payload, dict):
            raise ValueError("TTS preprocessing returned an invalid payload")

        reference_audio = payload.get("asr_format_audio_url")
        reference_text = payload.get("reference_audio_text")
        if not isinstance(reference_audio, str) or not reference_audio.strip():
            raise ValueError("TTS preprocessing did not return asr_format_audio_url")
        if not isinstance(reference_text, str) or not reference_text.strip():
            raise ValueError("TTS preprocessing did not return reference_audio_text")
        return payload

    @staticmethod
    def _require_wav_bytes(audio_data: bytes) -> bytes:
        if (
            not isinstance(audio_data, (bytes, bytearray))
            or len(audio_data) < 12
            or audio_data[:4] not in {b"RIFF", b"RF64"}
            or audio_data[8:12] != b"WAVE"
        ):
            raise ValueError("TTS synthesis did not return a valid WAV response")
        return bytes(audio_data)

    def extract_audio(self, video_path, audio_path):
        """Extract a WAV reference track with ffmpeg."""
        video_path = Path(video_path)
        audio_path = Path(audio_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        audio_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-y",
                    str(audio_path),
                ],
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            logger.error("Audio extraction failed: %s", exc)
            return False
        return audio_path.is_file()

    def train_voice_model(self, audio_path):
        """Call the configured TTS preprocessing endpoint and validate its contract."""
        audio_path = Path(audio_path)
        if not audio_path.is_file():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        tts_train_root = Path(TTS_TRAIN_DIR).parent.resolve()
        try:
            relative_path = audio_path.resolve().relative_to(tts_train_root)
        except ValueError as exc:
            raise ValueError("Reference audio must be stored below the configured TTS data directory") from exc

        response = requests.post(
            f"{TTS_URL}/v1/preprocess_and_tran",
            json={
                "format": "wav",
                "reference_audio": str(relative_path).replace("\\", "/"),
                "lang": "zh",
            },
            headers={"Content-Type": "application/json"},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("TTS preprocessing returned invalid JSON") from exc
        return self._require_training_result(payload)

    def synthesize_audio(self, text, reference_audio, reference_text, username):
        """Call the configured TTS endpoint and save a validated WAV response."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Text is required")
        if not isinstance(reference_audio, str) or not reference_audio.strip():
            raise ValueError("Reference audio is required")
        if not isinstance(reference_text, str) or not reference_text.strip():
            raise ValueError("Reference text is required")

        response = requests.post(
            f"{TTS_URL}/v1/invoke",
            json={
                "text": text,
                "reference_audio": reference_audio,
                "reference_text": reference_text,
                "format": "wav",
                "topP": 0.7,
                "max_new_tokens": 1024,
                "chunk_length": 100,
                "repetition_penalty": 1.2,
                "temperature": 0.7,
                "need_asr": False,
                "streaming": False,
                "is_fixed_seed": 0,
                "is_norm": 0,
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "audio/wav",
            },
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        audio_data = self._require_wav_bytes(response.content)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        audio_path = self._safe_user_output_dir(username) / f"audio_{timestamp}.wav"
        audio_path.write_bytes(audio_data)
        logger.info("Synthesized audio saved for user %s", username)
        return str(audio_path)
