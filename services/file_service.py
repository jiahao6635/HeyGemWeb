import logging
import os
from pathlib import Path
from datetime import datetime
from config import UPLOAD_DIR, TTS_TRAIN_DIR, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, upload_dir: Path = UPLOAD_DIR, tts_train_dir: Path = TTS_TRAIN_DIR):
        self.upload_dir = upload_dir
        self.tts_train_dir = tts_train_dir

    def check_file_extension(self, filename: str) -> bool:
        """检查文件扩展名是否允许"""
        return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

    def check_file_size(self, file_size: int) -> bool:
        """检查文件大小是否在限制范围内"""
        return file_size <= MAX_CONTENT_LENGTH

    def save_uploaded_file(self, file, filename: str) -> Path:
        """保存上传的文件"""
        if not self.check_file_extension(filename):
            raise ValueError("Unsupported file format")

        # 获取文件大小
        file_size = os.path.getsize(file.name)
        if not self.check_file_size(file_size):
            raise ValueError(f"File size exceeds maximum limit of {MAX_CONTENT_LENGTH // (1024*1024)}MB")

        # 使用时间戳生成文件名，与客户端保持一致
        ext = Path(filename).suffix
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # 格式：YYYYMMDDHHmmssSSS
        new_filename = f"{timestamp}{ext}"
        
        file_path = self.upload_dir / new_filename
        # 使用二进制模式复制文件
        with open(file.name, 'rb') as src, open(file_path, 'wb') as dst:
            dst.write(src.read())
            
        os.chmod(file_path, 0o644)
        logger.info(f"File saved: {file_path}")
        return file_path

    def get_audio_path(self, video_path: Path) -> Path:
        """获取对应的音频文件路径"""
        # 使用相同的时间戳文件名，只改变扩展名
        return self.tts_train_dir / f"{video_path.stem}.wav" 