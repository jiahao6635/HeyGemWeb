import os
import json
import requests
import logging
from pathlib import Path
from config import TTS_URL, VIDEO_URL, TTS_TRAIN_DIR, UPLOAD_DIR
from datetime import datetime

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        self.training_result = None

    def extract_audio(self, video_path, audio_path):
        """从视频中提取音频"""
        try:
            # 使用ffmpeg提取音频
            os.system(f'ffmpeg -i "{video_path}" -vn -acodec pcm_s16le -ar 44100 -ac 2 "{audio_path}"')
            return os.path.exists(audio_path)
        except Exception as e:
            logger.error(f"Error extracting audio: {str(e)}")
            return False

    def train_voice_model(self, audio_path):
        """训练语音模型"""
        try:
            # 确保音频文件存在
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # 获取相对路径
            audio_path = Path(audio_path)
            # 兼容多用户：取audio_path的父目录（即TTS_TRAIN_DIR/用户名）
            tts_train_root = TTS_TRAIN_DIR.parent
            relative_path = audio_path.relative_to(tts_train_root)
            reference_audio = str(relative_path).replace('\\', '/')  # 确保使用正斜杠

            # 准备训练参数
            data = {
                "format": "wav",
                "reference_audio": reference_audio,
                "lang": "zh"
            }

            logger.info(f"Sending training request with data: {data}")

            # 发送训练请求
            response = requests.post(
                f"{TTS_URL}/v1/preprocess_and_tran",
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            # 记录响应内容以便调试
            logger.info(f"Training response status: {response.status_code}")
            logger.info(f"Training response content: {response.text}")
            
            response.raise_for_status()
            
            # 保存训练结果
            result = response.json()
            self.training_result = result
            return result
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during training: {str(e)}")
            logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
            return None
        except Exception as e:
            logger.error(f"Error training voice model: {str(e)}")
            return None


    def synthesize_audio(self, text, reference_audio=None, reference_text=None, username=None):
        """合成音频"""
        try:
            # 使用保存的训练结果或传入的参数
            ref_audio = reference_audio or (self.training_result.get('asr_format_audio_url') if self.training_result else None)
            ref_text = reference_text or (self.training_result.get('reference_audio_text') if self.training_result else None)

            if not ref_audio or not ref_text:
                raise ValueError("Missing reference audio or text")

            # 准备合成参数
            data = {
                "text": text,
                "reference_audio": ref_audio,
                "reference_text": ref_text,
                "format": "wav",
                "topP": 0.7,
                "max_new_tokens": 1024,
                "chunk_length": 100,
                "repetition_penalty": 1.2,
                "temperature": 0.7,
                "need_asr": False,
                "streaming": False,
                "is_fixed_seed": 0,
                "is_norm": 0
            }

            logger.info(f"Sending synthesis request with data: {data}")

            # 发送合成请求，设置stream=True以获取二进制数据
            response = requests.post(
                f"{TTS_URL}/v1/invoke",
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "audio/wav"  # 指定接受音频数据
                },
                stream=True  # 启用流式传输
            )
            
            # 检查HTTP响应状态码，如果状态码不是200-299之间的值，将抛出HTTPError异常
            response.raise_for_status()
            
            # 获取音频数据（二进制数据）
            audio_data = response.raw.read()
            
            # 生成唯一的音频文件名
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
            audio_filename = f"audio_{timestamp}.wav"
            # 用户音频目录
            if username:
                user_audio_dir = UPLOAD_DIR / username
                user_audio_dir.mkdir(parents=True, exist_ok=True)
                audio_path = user_audio_dir / audio_filename
            else:
                UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
                audio_path = UPLOAD_DIR / audio_filename
            
            # 保存音频文件
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            logger.info(f"Audio saved to: {audio_path}")
            
            return str(audio_path)
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error during synthesis: {str(e)}")
            logger.error(f"Response content: {e.response.text if hasattr(e, 'response') else 'No response content'}")
            raise
        except Exception as e:
            logger.error(f"Error synthesizing audio: {str(e)}")
            raise 