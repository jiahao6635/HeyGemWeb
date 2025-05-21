import logging
import uuid
from pathlib import Path
import requests
from config import FACE2FACE_URL

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self, face2face_url: str = FACE2FACE_URL):
        self.face2face_url = face2face_url

    def make_video(self, video_path: Path, audio_path: Path) -> str:
        """生成视频"""
        try:
            task_id = str(uuid.uuid4())
            response = requests.post(
                self.face2face_url,
                json={
                    "audio_url": str(audio_path),
                    "video_url": str(video_path),
                    "code": task_id,
                    "chaofen": 0,
                    "watermark_switch": 0,
                    "pn": 1
                }
            )
            response.raise_for_status()
            logger.info(f"Video generation started. Task ID: {task_id}")
            return task_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Video generation API request failed: {str(e)}")
            raise

    def check_status(self, task_id: str) -> dict:
        """检查视频生成状态"""
        if not task_id:
            raise ValueError("Task ID is required")

        try:
            response = requests.get(
                f"{self.face2face_url}/status",
                params={"code": task_id}
            )
            response.raise_for_status()
            status_data = response.json()
            logger.info(f"Status checked for task {task_id}: {status_data}")
            return status_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Status check API request failed: {str(e)}")
            raise 