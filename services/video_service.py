import logging
import uuid
from pathlib import Path

import requests

from config import VIDEO_URL, UPLOAD_DIR


logger = logging.getLogger(__name__)


class VideoService:
    def __init__(self, face2face_url: str = VIDEO_URL, request_timeout=(5, 60)):
        self.face2face_url = face2face_url.rstrip("/")
        self.request_timeout = request_timeout

    @staticmethod
    def _require_file(path, label: str) -> Path:
        resolved = Path(path)
        if not resolved.is_file():
            raise FileNotFoundError(f"{label} file not found: {resolved}")
        return resolved

    @staticmethod
    def _parse_json_response(response, operation: str) -> dict:
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError(f"Video service returned invalid JSON during {operation}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"Video service returned an invalid payload during {operation}")
        return payload

    def make_video(self, video_path: Path, audio_path: Path, username: str = None) -> str:
        """Submit a video-generation task to the configured backend."""
        video_path = self._require_file(video_path, "Video")
        audio_path = self._require_file(audio_path, "Audio")

        if username:
            video_relative = f"{username}/{video_path.name}"
            audio_relative = f"{username}/{audio_path.name}"
        else:
            video_relative = video_path.name
            audio_relative = audio_path.name

        task_id = str(uuid.uuid4())
        data = {
            "audio_url": audio_relative,
            "video_url": video_relative,
            "code": task_id,
            "chaofen": 0,
            "watermark_switch": 0,
            "pn": 1,
        }

        logger.info("Submitting video task %s", task_id)
        response = requests.post(
            f"{self.face2face_url}/easy/submit",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        payload = self._parse_json_response(response, "submission")

        if payload.get("code") != 10000 or payload.get("success") is False:
            message = payload.get("msg") or f"business code {payload.get('code')}"
            raise RuntimeError(f"Video service rejected task submission: {message}")

        logger.info("Video task accepted: %s", task_id)
        return task_id

    def check_status(self, task_id: str) -> dict:
        """Return the validated JSON status payload for a backend task."""
        if not task_id:
            raise ValueError("Task ID is required")

        response = requests.get(
            f"{self.face2face_url}/easy/query",
            params={"code": task_id},
            headers={"Content-Type": "application/json"},
            timeout=self.request_timeout,
        )
        response.raise_for_status()
        return self._parse_json_response(response, "status query")

    def get_video_path(self, task_id: str, username: str = None) -> Path:
        """Return a safe completed-result path when the backend reports success."""
        status_data = self.check_status(task_id)
        if status_data.get("code") != 10000:
            raise ValueError("Video service status query failed")

        data = status_data.get("data") or {}
        if data.get("status") != 2:
            raise ValueError("Video not ready")

        raw_result = data.get("result")
        if not isinstance(raw_result, str) or not raw_result.strip():
            raise ValueError("Video service returned an empty result path")

        filename = Path(raw_result.replace("\\", "/")).name
        if not filename or Path(filename).suffix.lower() != ".mp4":
            raise ValueError("Video service returned an invalid result path")

        if username:
            return Path(UPLOAD_DIR) / username / filename
        return Path(raw_result)
