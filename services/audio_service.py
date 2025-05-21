import os
import json
import requests
import logging
from pathlib import Path
from config import TTS_URL,VIDEO_URL

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
            # 准备训练参数
            data = {
                "format": ".wav",
                "reference_audio": str(audio_path),
                "lang": "zh"
            }

            # 发送训练请求
            response = requests.post(TTS_URL + "/v1/preprocess_and_tran", json=data)
            response.raise_for_status()
            
            # 保存训练结果
            result = response.json()
            self.training_result = result
            return result
        except Exception as e:
            logger.error(f"Error training voice model: {str(e)}")
            return None

    def save_training_result(self, result):
        """保存训练结果"""
        self.training_result = result

    def synthesize_audio(self, voice_id, text, reference_audio=None, reference_text=None):
        """合成音频"""
        try:
            # 使用保存的训练结果或传入的参数
            ref_audio = reference_audio or (self.training_result.get('asr_format_audio_url') if self.training_result else None)
            ref_text = reference_text or (self.training_result.get('reference_audio_text') if self.training_result else None)

            if not ref_audio or not ref_text:
                raise ValueError("Missing reference audio or text")

            # 准备合成参数
            data = {
                "speaker": voice_id,
                "text": text,
                "reference_audio": ref_audio,
                "reference_text": ref_text
            }

            # 发送合成请求
            response = requests.post(TTS_URL + "/v1/invoke", json=data)
            response.raise_for_status()
            
            # 保存合成的音频
            result = response.json()
            audio_path = result.get('audio_path')
            
            if not audio_path:
                raise ValueError("No audio path in response")
                
            return audio_path
        except Exception as e:
            logger.error(f"Error synthesizing audio: {str(e)}")
            raise 