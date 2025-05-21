import os
from pathlib import Path

# 判断操作系统类型
IS_WINDOWS = os.name == 'nt'

# API endpoints - 所有服务都在同一台机器上，使用localhost
TTS_URL = "http://localhost:18180"  # 语音服务
VIDEO_URL = "http://localhost:8383"  # 视频服务基础URL

# File paths - 根据操作系统选择基础目录
if IS_WINDOWS:
    BASE_DIR = Path("D:/opt/heygem")  # Windows环境下的部署目录
else:
    BASE_DIR = Path("/root/heygem_data")  # Linux环境下的部署目录

UPLOAD_DIR = BASE_DIR / "face2face/temp"  # 模特视频
OUTPUT_DIR = BASE_DIR / "face2face/result"  # 输出视频
TTS_DIR = BASE_DIR / "voice"  # TTS相关文件
TTS_TRAIN_DIR = BASE_DIR / "voice/data/origin_audio"  # TTS训练文件
TTS_PRODUCT_DIR = BASE_DIR / "voice/data/processed_audio"  # TTS产物
LOG_DIR = BASE_DIR / "face2face/log"  # 日志目录

# Create directories if they don't exist and set permissions
for directory in [UPLOAD_DIR, OUTPUT_DIR, TTS_DIR, TTS_TRAIN_DIR, TTS_PRODUCT_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
    if not IS_WINDOWS:  # 只在Linux环境下设置权限
        os.chmod(directory, 0o755)

# Allowed video extensions
ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}

# Server configuration
SERVER_HOST = "0.0.0.0"  # 允许外部访问
SERVER_PORT = 2531  # Gradio服务端口

# Logging configuration
LOG_FILE = LOG_DIR / "heygem_web.log"
LOG_LEVEL = "INFO"

# Security settings
MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max file size 