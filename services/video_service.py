import logging
import uuid
from pathlib import Path
import requests
from config import VIDEO_URL, UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self, face2face_url: str = VIDEO_URL):
        self.face2face_url = face2face_url

    def make_video(self, video_path: Path, audio_path: Path, username: str = None) -> str:
        """生成视频，支持多用户隔离目录"""
        try:
            # 获取相对路径（带用户名）
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
                "pn": 1
            }
            logger.info(f"Sending video generation request with data: {data}")
            response = requests.post(
                f"{self.face2face_url}/easy/submit",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            logger.info(f"Video generation response status: {response.status_code}")
            logger.info(f"Video generation response content: {response.text}")
            response.raise_for_status()
            if not task_id:
                raise ValueError("No task ID in response")
            logger.info(f"Video generation started. Task ID: {task_id}")
            return task_id
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during video generation: {str(e)}")
            logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
            raise
        except Exception as e:
            logger.error(f"Error making video: {str(e)}")
            raise

    def check_status(self, task_id: str) -> dict:
        """检查视频生成状态"""
        if not task_id:
            raise ValueError("Task ID is required")

        try:
            # 发送状态查询请求
            response = requests.get(
                f"{self.face2face_url}/easy/query",
                params={"code": task_id},
                headers={"Content-Type": "application/json"}
            )
            
            # 记录响应内容以便调试
            logger.info(f"Status check response status: {response.status_code}")
            logger.info(f"Status check response content: {response.text}")
            
            response.raise_for_status()
            
            status_data = response.json()
            logger.info(f"Status checked for task {task_id}: {status_data}")
            return status_data
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during status check: {str(e)}")
            logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
            raise
        except Exception as e:
            logger.error(f"Error checking status: {str(e)}")
            raise

    def get_video_path(self, task_id: str, username: str = None) -> Path:
        """获取生成的视频文件路径，支持多用户隔离目录"""
        status_data = self.check_status(task_id)
        
        if status_data.get('code') == 10000:
            data = status_data.get('data', {})
            if data.get('status') == 2:  # 已完成
                video_path = data.get('result')
                if video_path:
                    if username:
                        return Path(UPLOAD_DIR) / username / Path(video_path).name
                    else:
                        return Path(video_path)
        
        raise ValueError("Video not found or not ready") 