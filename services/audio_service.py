import subprocess
import logging
import os
from pathlib import Path
import requests
from config import TTS_URL, TTS_TRAIN_DIR

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self, tts_url: str = TTS_URL):
        self.tts_url = tts_url
        # 确保输出目录存在
        TTS_TRAIN_DIR.mkdir(parents=True, exist_ok=True)
        if os.name != 'nt':  # 在Linux环境下设置权限
            os.chmod(TTS_TRAIN_DIR, 0o755)

    def extract_audio(self, video_path: Path, audio_path: Path) -> bool:
        """使用ffmpeg提取音频"""
        try:
            # 确保输出目录存在
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            if os.name != 'nt':  # 在Linux环境下设置权限
                os.chmod(audio_path.parent, 0o755)

            # 使用ffmpeg提取音频，参考客户端代码的参数
            result = subprocess.run([
                'ffmpeg',
                '-i', str(video_path),  # 输入视频
                '-vn',  # 不处理视频
                '-acodec', 'pcm_s16le',  # 音频编码为PCM
                '-ar', '16000',  # 采样率16kHz
                '-ac', '1',  # 单声道
                '-y',  # 覆盖已存在的文件
                str(audio_path)
            ], capture_output=True, text=True, check=True)
            
            logger.info(f"Audio extracted successfully to: {audio_path}")
            logger.debug(f"FFmpeg output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            return False

    def train_voice_model(self, audio_path: Path, language: str = "zh") -> str:
        """训练语音模型"""
        try:
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # 获取相对路径，类似于客户端代码中的处理方式
            relative_audio_path = str(audio_path.relative_to(TTS_TRAIN_DIR.parent.parent))
            logger.info(f"Training voice model with audio: {relative_audio_path}")

            response = requests.post(
                f"{self.tts_url}/train",
                json={
                    "audio_path": relative_audio_path,
                    "language": language
                }
            )
            response.raise_for_status()
            voice_id = response.json().get('voice_id')
            logger.info(f"Voice model trained successfully. Voice ID: {voice_id}")
            return voice_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Voice training API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during voice training: {str(e)}")
            raise

    def synthesize_audio(self, voice_id: str, text: str) -> str:
        """合成音频"""
        if not voice_id or not text:
            raise ValueError("Voice ID and text are required")

        try:
            response = requests.post(
                f"{self.tts_url}/synthesize",
                json={
                    "voice_id": voice_id,
                    "text": text
                }
            )
            response.raise_for_status()
            audio_path = response.json().get('audio_path')
            logger.info(f"Audio synthesized successfully: {audio_path}")
            return audio_path
        except requests.exceptions.RequestException as e:
            logger.error(f"Audio synthesis API request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during audio synthesis: {str(e)}")
            raise 