import os
from pathlib import Path

# 判断操作系统类型
IS_WINDOWS = os.name == 'nt'

# API endpoints - 默认服务位于本机，可通过环境变量覆盖
TTS_URL = os.getenv("HEYGEM_TTS_URL", "http://localhost:18180").rstrip("/")
VIDEO_URL = os.getenv("HEYGEM_VIDEO_URL", "http://localhost:8383").rstrip("/")

# File paths - 保留原有默认路径，同时允许部署和测试环境安全覆盖
DEFAULT_BASE_DIR = Path("D:/opt/heygem") if IS_WINDOWS else Path("/root/heygem_data")
BASE_DIR = Path(os.getenv("HEYGEM_BASE_DIR", str(DEFAULT_BASE_DIR))).expanduser().resolve()

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

# Allowed video extensions - 只允许MP4格式
ALLOWED_EXTENSIONS = {'.mp4'}

# Server configuration
SERVER_HOST = os.getenv("HEYGEM_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("HEYGEM_PORT", "2531"))

# Logging configuration
LOG_FILE = LOG_DIR / "heygem_web.log"
LOG_LEVEL = os.getenv("HEYGEM_LOG_LEVEL", "INFO").upper()

# Security settings
MAX_CONTENT_LENGTH = int(os.getenv("HEYGEM_MAX_UPLOAD_MB", "500")) * 1024 * 1024
