import logging
import os
import shutil
import tempfile
import threading
import concurrent.futures
from pathlib import Path
from datetime import datetime
from config import UPLOAD_DIR, TTS_TRAIN_DIR, ALLOWED_EXTENSIONS, MAX_CONTENT_LENGTH
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class FileService:
    def __init__(self, upload_dir: Path = UPLOAD_DIR, tts_train_dir: Path = TTS_TRAIN_DIR):
        self.upload_dir = upload_dir
        self.tts_train_dir = tts_train_dir

    def get_user_dir(self, username: str) -> Path:
        user_dir = self.upload_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir

    def get_user_tts_dir(self, username: str) -> Path:
        user_tts_dir = self.tts_train_dir / username
        user_tts_dir.mkdir(parents=True, exist_ok=True)
        return user_tts_dir

    def check_file_extension(self, filename: str) -> bool:
        """检查文件扩展名是否为MP4格式"""
        return Path(filename).suffix.lower() == '.mp4'

    def check_file_size(self, file_size: int) -> bool:
        """检查文件大小是否在限制范围内"""
        return file_size <= MAX_CONTENT_LENGTH

    def save_uploaded_file(self, file, filename: str, username: str) -> Path:
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
        
        user_dir = self.get_user_dir(username)
        file_path = user_dir / new_filename
        
        # 对于大文件，使用分块复制
        if file_size > 100 * 1024 * 1024:  # 100MB
            self._copy_large_file(file.name, file_path)
        else:
            # 使用二进制模式复制文件
            with open(file.name, 'rb') as src, open(file_path, 'wb') as dst:
                dst.write(src.read())
            
        os.chmod(file_path, 0o644)
        logger.info(f"File saved: {file_path}")
        return file_path

    def _copy_large_file(self, src_path: str, dst_path: Path, chunk_size: int = 8 * 1024 * 1024):
        """分块复制大文件，减少内存占用"""
        logger.info(f"使用分块复制处理大文件: {src_path} -> {dst_path}")
        
        try:
            with open(src_path, 'rb') as src, open(dst_path, 'wb') as dst:
                while True:
                    chunk = src.read(chunk_size)  # 每次读取8MB
                    if not chunk:
                        break
                    dst.write(chunk)
        except Exception as e:
            logger.error(f"分块复制文件失败: {str(e)}")
            # 如果复制失败，尝试删除目标文件
            if dst_path.exists():
                try:
                    dst_path.unlink()
                except:
                    pass
            raise

    def get_audio_path(self, video_path: Path, username: str) -> Path:
        """获取对应的音频文件路径"""
        # 使用相同的时间戳文件名，只改变扩展名
        user_tts_dir = self.get_user_tts_dir(username)
        return user_tts_dir / f"{video_path.stem}.wav"

    def scan_uploaded_videos(self, username: str) -> list[str]:
        """扫描已上传的MP4视频文件
        
        Returns:
            list[str]: 已上传MP4视频文件名称列表
        """
        videos = []
        try:
            user_dir = self.get_user_dir(username)
            # 扫描目录下的所有MP4文件
            for file_path in user_dir.glob('*.mp4'):
                if file_path.is_file():
                    videos.append(str(file_path.name))
            
            logger.info(f"Found {len(videos)} MP4 videos in {user_dir}")
            return videos
        except Exception as e:
            logger.error(f"Error scanning uploaded videos: {str(e)}")
            return []

    def scan_works(self, username: str) -> List[dict]:
        """扫描所有作品（以 -r.mp4 结尾）"""
        works = []
        user_dir = self.get_user_dir(username)
        for file in user_dir.glob("*-r.mp4"):
            file_info = self.get_file_info(file)
            if file_info:
                works.append(file_info)
        return works

    def scan_models(self, username: str) -> List[dict]:
        """扫描所有模特模型"""
        models = []
        user_dir = self.get_user_dir(username)
        for file in user_dir.glob("*.mp4"):
            if not file.name.endswith("-r.mp4"):
                file_info = self.get_file_info(file)
                if file_info:
                    models.append(file_info)
        return models

    def cleanup_temp_files(self, days_old: int = 7, username: str = None) -> dict:
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
        
        # 使用线程池进行并行清理
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            if username:
                # 清理用户目录
                user_dir = self.get_user_dir(username)
                futures.append(executor.submit(self._cleanup_directory, user_dir, cutoff_time, 'upload_dir', result))
                
                # 清理训练音频目录
                user_tts_dir = self.get_user_tts_dir(username)
                futures.append(executor.submit(self._cleanup_directory, user_tts_dir, cutoff_time, 'tts_train_dir', result))
                
                # 清理处理后的音频目录
                tts_product_dir = user_tts_dir.parent / 'processed_audio'
                futures.append(executor.submit(self._cleanup_directory, tts_product_dir, cutoff_time, 'tts_product_dir', result))
            else:
                # 全局清理（管理员用）
                futures.append(executor.submit(self._cleanup_directory, self.upload_dir, cutoff_time, 'upload_dir', result))
                futures.append(executor.submit(self._cleanup_directory, self.tts_train_dir, cutoff_time, 'tts_train_dir', result))
                tts_product_dir = self.tts_train_dir.parent / 'processed_audio'
                futures.append(executor.submit(self._cleanup_directory, tts_product_dir, cutoff_time, 'tts_product_dir', result))
            
            # 等待所有清理任务完成
            concurrent.futures.wait(futures)
        
        return result

    def _cleanup_directory(self, directory: Path, cutoff_time: float, result_key: str, result: Dict[str, Dict[str, int]]):
        """清理指定目录中的过期文件"""
        try:
            for file_path in directory.glob('*'):
                try:
                    if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        result[result_key]['deleted'] += 1
                except Exception as e:
                    logger.error(f"删除文件失败 {file_path}: {str(e)}")
                    result[result_key]['failed'] += 1
        except Exception as e:
            logger.error(f"清理目录失败 {directory}: {str(e)}")

    def get_file_info(self, file_path: Path) -> dict:
        """获取文件信息"""
        try:
            stat = file_path.stat()
            return {
                "name": file_path.stem,
                "path": str(file_path),
                "created_time": stat.st_ctime,
                "size": stat.st_size,
                "thumbnail": self._generate_thumbnail(file_path) if file_path.suffix.lower() in ['.mp4', '.jpg', '.png'] else None
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {str(e)}")
            return None

    def _generate_thumbnail(self, file_path: Path) -> str:
        """生成视频或图片的缩略图"""
        try:
            if file_path.suffix.lower() == '.mp4':
                # 使用 ffmpeg 生成视频缩略图
                thumbnail_path = file_path.parent / f"{file_path.stem}_thumb.jpg"
                if not thumbnail_path.exists():
                    import subprocess
                    subprocess.run([
                        'ffmpeg', '-i', str(file_path),
                        '-ss', '00:00:01', '-vframes', '1',
                        str(thumbnail_path)
                    ], capture_output=True)
                return str(thumbnail_path)
            elif file_path.suffix.lower() in ['.jpg', '.png']:
                # 图片直接返回路径
                return str(file_path)
            return None
        except Exception as e:
            logger.error(f"生成缩略图失败: {str(e)}")
            return None 