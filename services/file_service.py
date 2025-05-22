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
        """检查文件扩展名是否为MP4格式"""
        return Path(filename).suffix.lower() == '.mp4'

    def check_file_size(self, file_size: int) -> bool:
        """检查文件大小是否在限制范围内"""
        return file_size <= MAX_CONTENT_LENGTH

    def save_uploaded_file(self, file, filename: str) -> Path:
        """保存上传的文件"""
        if not self.check_file_extension(filename):
            raise ValueError("只支持MP4格式的视频文件")

        # 获取文件大小
        file_size = os.path.getsize(file.name)
        if not self.check_file_size(file_size):
            raise ValueError(f"文件大小超过限制 {MAX_CONTENT_LENGTH // (1024*1024)}MB")

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

    def scan_uploaded_videos(self) -> list[str]:
        """扫描已上传的MP4视频文件
        
        Returns:
            list[str]: 已上传MP4视频文件的路径列表
        """
        videos = []
        try:
            # 确保目录存在
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            
            # 扫描目录下的所有MP4文件
            for file_path in self.upload_dir.glob('*.mp4'):
                if file_path.is_file():
                    videos.append(str(file_path))
            
            logger.info(f"Found {len(videos)} MP4 videos in {self.upload_dir}")
            return videos
        except Exception as e:
            logger.error(f"Error scanning uploaded videos: {str(e)}")
            return []

    def cleanup_temp_files(self, days_old: int = 7) -> dict:
        """清理临时文件
        
        Args:
            days_old: 清理多少天前的文件，默认7天
            
        Returns:
            dict: 包含清理结果的字典
        """
        from datetime import datetime, timedelta
        import time
        
        result = {
            'upload_dir': {'deleted': 0, 'failed': 0},
            'tts_train_dir': {'deleted': 0, 'failed': 0},
            'tts_product_dir': {'deleted': 0, 'failed': 0}
        }
        
        # 计算截止时间
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        # 清理上传目录
        for file_path in self.upload_dir.glob('*'):
            try:
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    result['upload_dir']['deleted'] += 1
            except Exception as e:
                logger.error(f"删除文件失败 {file_path}: {str(e)}")
                result['upload_dir']['failed'] += 1
        
        # 清理训练音频目录
        for file_path in self.tts_train_dir.glob('*'):
            try:
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    result['tts_train_dir']['deleted'] += 1
            except Exception as e:
                logger.error(f"删除文件失败 {file_path}: {str(e)}")
                result['tts_train_dir']['failed'] += 1
        
        # 清理处理后的音频目录
        tts_product_dir = self.tts_train_dir.parent / 'processed_audio'
        for file_path in tts_product_dir.glob('*'):
            try:
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    result['tts_product_dir']['deleted'] += 1
            except Exception as e:
                logger.error(f"删除文件失败 {file_path}: {str(e)}")
                result['tts_product_dir']['failed'] += 1
        
        return result 