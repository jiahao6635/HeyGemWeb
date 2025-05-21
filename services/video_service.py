import logging
import uuid
from pathlib import Path
import requests
from config import VIDEO_URL

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self, face2face_url: str = VIDEO_URL):
        self.face2face_url = face2face_url

    def make_video(self, video_path: Path, audio_path: Path) -> str:
        """生成视频"""
        try:
            # 准备请求参数
            data = {
                "audio_url": str(audio_path),
                "video_url": str(video_path),
                "code": str(video_path.stem)  # 使用视频文件名作为code
            }

            # 发送视频合成请求
            response = requests.post(self.face2face_url + "/easy/submit", json=data)
            response.raise_for_status()
            
            # 返回任务ID
            result = response.json()
            task_id = result.get('code')
            
            if not task_id:
                raise ValueError("No task ID in response")
                
            logger.info(f"Video generation started. Task ID: {task_id}")
            return task_id
        except Exception as e:
            logger.error(f"Error making video: {str(e)}")
            raise

    def check_status(self, task_id: str) -> dict:
        """检查视频生成状态"""
        if not task_id:
            raise ValueError("Task ID is required")

        try:
            # 发送状态查询请求
            response = requests.get(f"{self.face2face_url}/easy/query", params={"code": task_id})
            response.raise_for_status()
            
            status_data = response.json()
            logger.info(f"Status checked for task {task_id}: {status_data}")
            return status_data
        except Exception as e:
            logger.error(f"Error checking status: {str(e)}")
            raise 