import logging
import uuid
import os
import tempfile
import threading
import concurrent.futures
import subprocess
import shutil
from pathlib import Path
import requests
from config import VIDEO_URL, UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

class VideoService:
    def __init__(self, face2face_url: str = VIDEO_URL):
        self.face2face_url = face2face_url
        self.max_workers = min(os.cpu_count() or 4, 4)  # 最大并行工作线程数
        self.chunk_size = 10  # 视频分段处理，每段秒数

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
            
            # 检查文件大小，大文件使用优化处理
            video_size = video_path.stat().st_size
            if video_size > 100 * 1024 * 1024:  # 100MB
                logger.info(f"大文件视频处理: {video_path} ({video_size / (1024*1024):.2f} MB)")
                # 大文件使用异步处理
                threading.Thread(
                    target=self._process_large_video,
                    args=(video_path, audio_path, task_id, username),
                    daemon=True
                ).start()
                return task_id
            
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

    def _process_large_video(self, video_path: Path, audio_path: Path, task_id: str, username: str = None):
        """处理大型视频文件，使用分段并行处理"""
        try:
            logger.info(f"开始大型视频处理: {video_path}, 任务ID: {task_id}")
            
            # 创建临时工作目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                
                # 1. 获取视频时长
                duration = self._get_video_duration(video_path)
                logger.info(f"视频时长: {duration}秒")
                
                # 2. 分段视频
                segments = []
                for i in range(0, int(duration), self.chunk_size):
                    segment_path = temp_dir_path / f"segment_{i}.mp4"
                    end_time = min(i + self.chunk_size, duration)
                    self._extract_video_segment(video_path, segment_path, i, end_time)
                    segments.append(segment_path)
                
                logger.info(f"视频已分割为 {len(segments)} 个片段")
                
                # 3. 分段音频
                audio_segments = []
                for i in range(0, int(duration), self.chunk_size):
                    segment_path = temp_dir_path / f"audio_{i}.wav"
                    end_time = min(i + self.chunk_size, duration)
                    self._extract_audio_segment(audio_path, segment_path, i, end_time)
                    audio_segments.append(segment_path)
                
                # 4. 并行处理每个片段
                processed_segments = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = []
                    for i, (video_segment, audio_segment) in enumerate(zip(segments, audio_segments)):
                        output_path = temp_dir_path / f"processed_{i}.mp4"
                        futures.append(
                            executor.submit(
                                self._process_video_segment, 
                                video_segment, 
                                audio_segment, 
                                output_path
                            )
                        )
                    
                    # 等待所有处理完成
                    for i, future in enumerate(concurrent.futures.as_completed(futures)):
                        try:
                            result_path = future.result()
                            processed_segments.append((i, result_path))
                            logger.info(f"片段 {i} 处理完成: {result_path}")
                        except Exception as e:
                            logger.error(f"片段 {i} 处理失败: {str(e)}")
                
                # 5. 合并处理后的片段
                processed_segments.sort()  # 按索引排序
                segment_files = [str(path) for _, path in processed_segments]
                
                # 准备合并文件列表
                concat_file = temp_dir_path / "concat.txt"
                with open(concat_file, "w") as f:
                    for segment in segment_files:
                        f.write(f"file '{segment}'\n")
                
                # 合并输出文件路径
                output_filename = f"{video_path.stem}-r.mp4"
                if username:
                    output_path = UPLOAD_DIR / username / output_filename
                else:
                    output_path = OUTPUT_DIR / output_filename
                
                # 确保输出目录存在
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 执行合并
                self._merge_video_segments(concat_file, output_path)
                
                logger.info(f"大型视频处理完成: {output_path}")
                
                # 更新任务状态（模拟API响应）
                self._update_task_status(task_id, str(output_path))
                
        except Exception as e:
            logger.error(f"大型视频处理失败: {str(e)}")
            # 更新任务状态为失败
            self._update_task_status(task_id, None, error=str(e))

    def _get_video_duration(self, video_path: Path) -> float:
        """获取视频时长（秒）"""
        cmd = [
            "ffprobe", 
            "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip())

    def _extract_video_segment(self, video_path: Path, output_path: Path, start_time: int, end_time: int):
        """提取视频片段"""
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c:v", "copy",  # 复制视频流，不重新编码
            "-an",  # 不包含音频
            "-y",  # 覆盖输出文件
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _extract_audio_segment(self, audio_path: Path, output_path: Path, start_time: int, end_time: int):
        """提取音频片段"""
        cmd = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ss", str(start_time),
            "-to", str(end_time),
            "-c:a", "copy",  # 复制音频流，不重新编码
            "-y",  # 覆盖输出文件
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _process_video_segment(self, video_segment: Path, audio_segment: Path, output_path: Path) -> Path:
        """处理单个视频片段"""
        # 这里调用实际的处理逻辑，可以是API调用或本地处理
        # 简化示例：合并视频和音频
        cmd = [
            "ffmpeg",
            "-i", str(video_segment),
            "-i", str(audio_segment),
            "-c:v", "copy",
            "-c:a", "aac",
            "-strict", "experimental",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            "-y",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def _merge_video_segments(self, concat_file: Path, output_path: Path):
        """合并视频片段"""
        cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            "-y",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)

    def _update_task_status(self, task_id: str, result_path: str = None, error: str = None):
        """更新任务状态（模拟API响应）"""
        # 实际实现中，这里应该更新数据库或缓存中的任务状态
        logger.info(f"更新任务状态: {task_id}, 结果: {result_path}, 错误: {error}")
        # 这里只是记录日志，实际应用中应该实现持久化存储

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