from dotenv import load_dotenv
load_dotenv()

import logging
import gradio as gr
import os
import threading

from pathlib import Path
from config import (
    SERVER_HOST,
    SERVER_PORT,
    LOG_FILE,
    LOG_LEVEL,
    LOG_DIR,
    UPLOAD_DIR,
    OUTPUT_DIR,
    BASE_DIR,
)
from services.audio_service import AudioService
from services.video_service import VideoService
from services.file_service import FileService
from services.task_service import TaskService, TaskType, TaskPriority, TaskStatus
from datetime import datetime
import json

# 确保日志目录存在
LOG_DIR.mkdir(parents=True, exist_ok=True)

# 配置日志
try:
    logging.basicConfig(
        filename=LOG_FILE,
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
except Exception as e:
    print(f"警告: 文件日志配置失败: {e}")
    # 如果文件日志配置失败，使用控制台日志
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)

def _is_safe_account_name(username: str) -> bool:
    """Return whether an account name is safe to use as a directory name."""
    return bool(
        username
        and username == username.strip()
        and username not in {".", ".."}
        and "/" not in username
        and "\\" not in username
        and "\x00" not in username
    )


def load_credentials(environ=None):
    """Load up to ten Gradio auth accounts without failing module imports."""
    if environ is None:
        environ = os.environ
    credentials = {}
    errors = []

    for index in range(1, 11):
        username = environ.get(f"USER_{index}_NAME")
        password = environ.get(f"USER_{index}_PASSWORD")

        if not username and not password:
            continue
        if not username or not password:
            errors.append(f"USER_{index}_NAME and USER_{index}_PASSWORD must be configured together")
            continue
        if not _is_safe_account_name(username):
            errors.append(f"USER_{index}_NAME is not safe for a storage namespace")
            continue
        if username in credentials:
            errors.append(f"duplicate configured username: {username}")
            continue

        credentials[username] = password

    return credentials, errors


VALID_CREDENTIALS, CREDENTIAL_ERRORS = load_credentials()


def validate_auth_configuration():
    """Validate credentials only when the server is actually launched."""
    if CREDENTIAL_ERRORS:
        raise RuntimeError("Invalid authentication configuration: " + "; ".join(CREDENTIAL_ERRORS))
    if not VALID_CREDENTIALS:
        raise RuntimeError(
            "No login account is configured. Set USER_1_NAME and USER_1_PASSWORD before starting HeyGemWeb."
        )


def require_username(request: gr.Request) -> str:
    """Read the authenticated user supplied by Gradio's server-side auth."""
    username = getattr(request, "username", None)
    if not username or username not in VALID_CREDENTIALS:
        raise gr.Error("Authentication required.")
    return username


def classify_video_status(status) -> str:
    """Normalize status codes used by HeyGem-compatible video backends."""
    if status == 1:
        return "processing"
    if status == 2:
        return "completed"
    if status in {0, 3}:
        return "failed"
    return "unknown"

custom_css = """
/* 隐藏 Gradio 页脚 */
footer { display: none !important; }
/* 隐藏 Gradio 顶部Logo和标题栏 */
#logo, .prose { display: none !important; }
/* 隐藏加载动画 */
#loading, .loading { display: none !important; }
/* 隐藏 gradio 右下角的反馈按钮 */
.gradio-app .fixed.bottom-4.right-4, .feedback { display: none !important; }

/* 自定义字体设置 */
@font-face {
    font-family: 'System UI';
    src: local('system-ui');
    font-weight: normal;
    font-style: normal;
}

@font-face {
    font-family: 'System UI';
    src: local('system-ui');
    font-weight: bold;
    font-style: normal;
}

/* 基础样式设置 */
:root {
    --primary-color: #4f46e5;
    --primary-color-hover: #4338ca;
    --secondary-color: #10b981;
    --secondary-color-hover: #059669;
    --text-color: #1f2937;
    --text-color-light: #6b7280;
    --bg-color: #ffffff;
    --bg-color-secondary: #f9fafb;
    --border-color: #e5e7eb;
    --shadow-color: rgba(0, 0, 0, 0.1);
    --radius: 8px;
    --transition: all 0.3s ease;
}

/* 深色模式 */
@media (prefers-color-scheme: dark) {
    :root {
        --primary-color: #6366f1;
        --primary-color-hover: #4f46e5;
        --secondary-color: #10b981;
        --secondary-color-hover: #059669;
        --text-color: #f9fafb;
        --text-color-light: #d1d5db;
        --bg-color: #111827;
        --bg-color-secondary: #1f2937;
        --border-color: #374151;
        --shadow-color: rgba(0, 0, 0, 0.3);
    }
}

/* 手动切换深色模式 */
.dark-theme {
    --primary-color: #6366f1;
    --primary-color-hover: #4f46e5;
    --secondary-color: #10b981;
    --secondary-color-hover: #059669;
    --text-color: #f9fafb;
    --text-color-light: #d1d5db;
    --bg-color: #111827;
    --bg-color-secondary: #1f2937;
    --border-color: #374151;
    --shadow-color: rgba(0, 0, 0, 0.3);
}

/* 使用系统字体作为后备 */
body {
    font-family: 'System UI', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
    color: var(--text-color);
    background-color: var(--bg-color);
    transition: var(--transition);
    margin: 0;
    padding: 0;
}

/* 容器样式 */
.gradio-container {
    max-width: 1200px !important;
    margin: 0 auto !important;
    padding: 1rem !important;
}

/* 按钮样式 */
button, .gr-button {
    background-color: var(--primary-color) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius) !important;
    padding: 0.5rem 1rem !important;
    font-weight: 500 !important;
    transition: var(--transition) !important;
    cursor: pointer !important;
    box-shadow: 0 1px 3px var(--shadow-color) !important;
}

button:hover, .gr-button:hover {
    background-color: var(--primary-color-hover) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 6px var(--shadow-color) !important;
}

/* 输入框样式 */
input, textarea, select, .gr-input, .gr-textarea, .gr-select {
    border: 1px solid var(--border-color) !important;
    border-radius: var(--radius) !important;
    padding: 0.5rem !important;
    background-color: var(--bg-color) !important;
    color: var(--text-color) !important;
    transition: var(--transition) !important;
}

input:focus, textarea:focus, select:focus, .gr-input:focus, .gr-textarea:focus, .gr-select:focus {
    border-color: var(--primary-color) !important;
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2) !important;
}

/* 标签页样式 */
.tabs {
    border-bottom: 1px solid var(--border-color) !important;
    margin-bottom: 1rem !important;
}

.tab-button {
    background: none !important;
    border: none !important;
    padding: 0.75rem 1rem !important;
    color: var(--text-color-light) !important;
    font-weight: 500 !important;
    border-bottom: 2px solid transparent !important;
    transition: var(--transition) !important;
}

.tab-button.selected, .tab-button:hover {
    color: var(--primary-color) !important;
    border-bottom-color: var(--primary-color) !important;
    background-color: transparent !important;
}

/* 卡片样式 */
.gr-box, .gr-panel {
    border-radius: var(--radius) !important;
    border: 1px solid var(--border-color) !important;
    background-color: var(--bg-color) !important;
    box-shadow: 0 1px 3px var(--shadow-color) !important;
    transition: var(--transition) !important;
}

.gr-box:hover, .gr-panel:hover {
    box-shadow: 0 4px 6px var(--shadow-color) !important;
}

/* 标题样式 */
h1, h2, h3, h4, h5, h6 {
    color: var(--text-color) !important;
    margin-top: 0 !important;
}

h1 {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    margin-bottom: 1.5rem !important;
    color: var(--primary-color) !important;
}

/* 图库样式 */
.gallery {
    display: grid !important;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)) !important;
    gap: 1rem !important;
}

.gallery-item {
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    box-shadow: 0 1px 3px var(--shadow-color) !important;
    transition: var(--transition) !important;
}

.gallery-item:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 6px var(--shadow-color) !important;
}

/* 响应式布局 */
@media (max-width: 768px) {
    .gradio-container {
        padding: 0.5rem !important;
        width: 100% !important;
        max-width: 100% !important;
    }
    
    .gr-row {
        flex-direction: column !important;
    }
    
    .gr-col {
        width: 100% !important;
        margin-bottom: 1rem !important;
    }
    
    .gallery {
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)) !important;
    }
    
    h1 {
        font-size: 1.5rem !important;
    }
    
    button, .gr-button {
        width: 100% !important;
        margin-bottom: 0.5rem !important;
    }
    
    input, textarea, select {
        font-size: 16px !important; /* 防止iOS缩放 */
    }
    
    /* 改进移动端标签页 */
    .tabs {
        overflow-x: auto !important;
        white-space: nowrap !important;
        -webkit-overflow-scrolling: touch !important;
    }
    
    .tab-button {
        padding: 0.5rem 0.75rem !important;
    }
}

/* 更小屏幕的优化 */
@media (max-width: 480px) {
    .gallery {
        grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)) !important;
    }
    
    h1 {
        font-size: 1.3rem !important;
    }
}

/* 动画效果 */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.gr-box, .gr-panel, .gr-form {
    animation: fadeIn 0.3s ease-out;
}
"""

class HeyGemApp:
    def __init__(self):
        self.audio_service = AudioService()
        self.video_service = VideoService()
        self.file_service = FileService()
        self.task_service = TaskService()
        self.video_task_lock = threading.Lock()
        self.video_task_db_path = BASE_DIR / "video_tasks.json"
        self.video_task_owners = self._load_video_task_owners()
        
        # 启动任务队列服务
        self.task_service.start()

    def get_owned_task(self, task_id: str, username: str):
        """Return a task only when it belongs to the authenticated user."""
        task = self.task_service.get_task(task_id)
        if not isinstance(task, dict) or task.get("username") != username:
            return None
        return task

    def _load_video_task_owners(self):
        if not self.video_task_db_path.is_file():
            return {}
        try:
            with open(self.video_task_db_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if not isinstance(payload, dict):
                raise ValueError("video task registry must be a JSON object")
            return {
                str(task_id): username
                for task_id, username in payload.items()
                if isinstance(username, str) and username
            }
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logger.warning("无法读取视频任务归属记录: %s", exc)
            return {}

    def record_video_task_owner(self, task_id: str, username: str):
        with self.video_task_lock:
            self.video_task_owners[task_id] = username
            temp_path = self.video_task_db_path.with_suffix(".tmp")
            try:
                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(self.video_task_owners, f, ensure_ascii=False, indent=2)
                if os.name != "nt":
                    os.chmod(temp_path, 0o600)
                temp_path.replace(self.video_task_db_path)
            except OSError as exc:
                logger.warning("无法持久化视频任务归属记录: %s", exc)

    def _move_video_to_user_dir(self, video_filename, username):
        """移动视频文件到用户目录"""
        try:
            if not isinstance(video_filename, str) or not video_filename.strip():
                return False, "视频服务未返回结果文件", None

            safe_filename = Path(video_filename.replace("\\", "/")).name
            if not safe_filename or Path(safe_filename).suffix.lower() != ".mp4":
                return False, "视频服务返回了无效的结果文件", None

            user_dir = self.file_service.get_user_dir(username)
            target_path = user_dir / safe_filename

            if target_path.is_file():
                return True, f"视频已保存到: {target_path}", target_path

            source_candidates = [UPLOAD_DIR / safe_filename, OUTPUT_DIR / safe_filename]
            source_path = next((path for path in source_candidates if path.is_file()), None)
            if source_path is None:
                return False, f"视频文件不存在: {safe_filename}", None

            source_path.rename(target_path)
            return True, f"视频已保存到: {target_path}", target_path
            
        except Exception as e:
            logger.error(f"移动视频文件失败: {str(e)}")
            return False, f"移动视频文件失败: {str(e)}", None

    def _cleanup_temp_images(self, username):
        """清理临时图片文件"""
        try:
            cleaned_files = []
            user_dir = self.file_service.get_user_dir(username)
            for temp_file in user_dir.glob("*.png"):
                if temp_file.name.replace(".png", "").isdigit():
                    temp_file.unlink()
                    cleaned_files.append(temp_file.name)
            
            if cleaned_files:
                logger.info(f"已清理临时图片文件: {', '.join(cleaned_files)}")
                return True, f"已清理 {len(cleaned_files)} 个临时文件"
            return True, "没有需要清理的临时文件"
            
        except Exception as e:
            logger.error(f"清理临时图片文件失败: {str(e)}")
            return False, f"清理临时文件失败: {str(e)}"

    def create_interface(self):
        with gr.Blocks(title="HeyGem数字人") as demo:
            theme_state = gr.State(value="light")
            with gr.Group():
                with gr.Row():
                    gr.Markdown("# HeyGem数字人界面")
                    with gr.Column(scale=1, min_width=100):
                        theme_btn = gr.Button("🌓 切换深色/浅色模式", scale=0)
                with gr.Tab("我的作品"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            works_gallery = gr.Gallery(
                                label="我的作品",
                                show_label=True,
                                elem_id="works_gallery",
                                columns=4,
                                allow_preview=True,
                                height="auto",
                                object_fit="contain",
                                min_width=160
                            )
                    with gr.Row():
                        refresh_btn = gr.Button("刷新作品列表")
                        selected_video = gr.State(value=None)
                with gr.Tab("我的数字模特"):
                    with gr.Row():
                        with gr.Column(scale=1):
                            models_gallery = gr.Gallery(
                                label="我的数字模特",
                                show_label=True,
                                elem_id="models_gallery",
                                columns=4,
                                allow_preview=True,
                                height="auto",
                                object_fit="contain",
                                min_width=160
                            )
                    with gr.Row():
                        refresh_models_btn = gr.Button("刷新模特列表")
                        selected_model = gr.State(value=None)
                with gr.Tab("模型训练"):
                    with gr.Row():
                        with gr.Column():
                            video_input = gr.File(label="上传视频", file_types=[".mp4"], type="filepath")
                            model_name = gr.Textbox(label="模特名称", placeholder="请输入模特名称")
                            train_btn = gr.Button("开始训练")
                            train_output = gr.Textbox(label="训练状态", lines=5)
                with gr.Tab("视频生成"):
                    with gr.Row():
                        with gr.Column():
                            video_path_input = gr.Textbox(
                                label="选择数字人模特",
                                placeholder="请输入模特名称（例如：model1）",
                                value=None
                            )
                            text_input = gr.Textbox(label="要合成的文本", lines=3)
                            generate_btn = gr.Button("生成视频")
                            task_id_output = gr.Textbox(label="任务ID")
                            check_status_btn = gr.Button("检查状态")
                            status_output = gr.Textbox(label="状态", lines=3)
                            
                            # 添加操作引导
                            gr.Markdown("""
                            ### 操作指南
                            1. 输入模特名称（在"我的数字模特"中可以查看）
                            2. 输入要合成的文本
                            3. 点击"生成视频"按钮开始任务
                            4. 点击"检查状态"查询后端任务进度
                            5. 任务完成后，可以在"我的作品"中查看生成的视频
                            
                            > **提示**：生成视频可能需要几分钟时间，请耐心等待
                            """)
                with gr.Tab("文件清理"):
                    with gr.Row():
                        with gr.Column():
                            days_input = gr.Number(
                                label="清理多少天前的文件",
                                value=7,
                                minimum=1,
                                maximum=365,
                                step=1
                            )
                            cleanup_btn = gr.Button("开始清理")
                            cleanup_output = gr.Textbox(label="清理结果", lines=10)
                
                with gr.Tab("帮助与反馈"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("""
                            # 帮助文档
                            
                            ## 基本功能
                            
                            ### 模型训练
                            1. 上传一段清晰的视频文件（MP4格式）
                            2. 输入模特名称
                            3. 点击"开始训练"按钮
                            4. 等待训练完成（可在任务队列中查看进度）
                            
                            ### 视频生成
                            1. 输入已训练好的模特名称
                            2. 输入要合成的文本
                            3. 点击"生成视频"按钮
                            4. 等待生成完成（可在任务队列中查看进度）
                            
                            ### 文件管理
                            - 在"我的作品"中查看所有生成的视频
                            - 在"我的数字模特"中查看所有训练好的模型
                            - 使用"文件清理"功能定期清理临时文件
                            
                            ### 任务队列
                            - 查看所有任务的状态和进度
                            - 取消等待中的任务
                            
                            ## 常见问题
                            
                            **Q: 为什么我的视频生成失败了？**  
                            A: 可能是以下原因：
                            - 模特名称输入错误
                            - 文本内容过长或包含特殊字符
                            - 系统资源不足
                            
                            **Q: 如何提高视频生成质量？**  
                            A: 请确保：
                            - 上传高质量的原始视频
                            - 确保视频中人物面部清晰可见
                            - 避免背景噪音和干扰
                            
                            **Q: 文件会自动删除吗？**  
                            A: 系统默认不会自动删除文件，需要手动使用"文件清理"功能。
                            """)
                        
                        with gr.Column(scale=1):
                            gr.Markdown("## 用户反馈")
                            feedback_type = gr.Radio(
                                ["问题报告", "功能建议", "其他反馈"],
                                label="反馈类型",
                                value="问题报告"
                            )
                            feedback_content = gr.Textbox(
                                label="反馈内容",
                                placeholder="请详细描述您的问题或建议...",
                                lines=5
                            )
                            feedback_email = gr.Textbox(
                                label="联系邮箱（选填）",
                                placeholder="example@email.com"
                            )
                            feedback_btn = gr.Button("提交反馈")
                            feedback_status = gr.Textbox(label="提交状态", interactive=False)
                with gr.Tab("任务队列"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            gr.Markdown("### 任务队列状态")
                            queue_status = gr.JSON(label="队列状态")
                            refresh_queue_btn = gr.Button("刷新队列状态")
                                
                        with gr.Column(scale=3):
                            gr.Markdown("### 我的任务")
                            user_tasks = gr.Dataframe(
                                headers=["任务ID", "类型", "状态", "进度", "创建时间", "操作"],
                                datatype=["str", "str", "str", "number", "str", "str"],
                                row_count=10,
                                column_count=(6, "fixed"),
                                interactive=False
                            )
                            refresh_tasks_btn = gr.Button("刷新我的任务")
                            
                            gr.Markdown("### 任务操作")
                            with gr.Row():
                                task_id_input = gr.Textbox(label="任务ID", placeholder="输入要操作的任务ID")
                                cancel_task_btn = gr.Button("取消任务", variant="stop")
                            task_details = gr.JSON(label="任务详情")
                            get_task_btn = gr.Button("获取任务详情")
                # --- 任务队列逻辑 ---
                def get_queue_status(request: gr.Request):
                    require_username(request)
                    return self.task_service.get_queue_status()
                
                def get_user_tasks(request: gr.Request):
                    username = require_username(request)
                    tasks = self.task_service.get_user_tasks(username)
                    # 格式化为表格显示
                    rows = []
                    for task in tasks:
                        task_id = task["task_id"]
                        task_type = task["task_type"]
                        status = task["status"]
                        progress = task["progress"]
                        created_at = datetime.fromisoformat(task["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
                        action = "取消" if status == TaskStatus.PENDING else "-"
                        rows.append([task_id, task_type, status, progress, created_at, action])
                    
                    return rows
                
                def get_task_details(task_id, request: gr.Request):
                    if not task_id:
                        return {"error": "请输入任务ID"}

                    username = require_username(request)
                    task = self.get_owned_task(task_id, username)
                    if not task:
                        return {"error": "未找到任务"}

                    return task
                
                def cancel_task(task_id, request: gr.Request):
                    if not task_id:
                        return {"error": "请输入任务ID"}

                    username = require_username(request)
                    task = self.get_owned_task(task_id, username)
                    if not task:
                        return {"error": "未找到任务"}

                    success = self.task_service.cancel_task(task_id)
                    if success:
                        return {"success": f"已取消任务 {task_id}"}
                    else:
                        return {"error": f"无法取消任务 {task_id}"}
                
                # 绑定任务队列相关事件
                refresh_queue_btn.click(get_queue_status, None, queue_status)
                refresh_tasks_btn.click(get_user_tasks, None, user_tasks)
                get_task_btn.click(get_task_details, task_id_input, task_details)
                cancel_task_btn.click(cancel_task, task_id_input, task_details)
                
                # 页面加载时自动刷新
                demo.load(fn=get_queue_status, inputs=None, outputs=queue_status)
                demo.load(fn=get_user_tasks, inputs=None, outputs=user_tasks)
                
                # --- 深色模式切换逻辑 ---
                def toggle_theme(current_theme):
                    if current_theme == "light":
                        # 切换到深色模式
                        return "dark"
                    else:
                        # 切换到浅色模式
                        return "light"
                
                theme_btn.click(
                    fn=toggle_theme,
                    inputs=[theme_state],
                    outputs=[theme_state]
                )
                
                # --- 我的作品逻辑 ---
                def get_gallery_items(request: gr.Request):
                    username = require_username(request)
                    return [(w["path"], w["name"]) for w in self.get_works_info(username)]

                def get_models_items(request: gr.Request):
                    username = require_username(request)
                    return [(m["path"], m["name"]) for m in self.get_models_info(username)]

                def select_video(evt: gr.SelectData, request: gr.Request):
                    username = require_username(request)
                    works = self.get_works_info(username)
                    selected = works[evt.index]
                    return selected["path"]

                def select_model(evt: gr.SelectData, request: gr.Request):
                    username = require_username(request)
                    models = self.get_models_info(username)
                    selected = models[evt.index]
                    return selected["path"]
                works_gallery.select(select_video, outputs=selected_video)
                refresh_btn.click(get_gallery_items, None, works_gallery)
                models_gallery.select(select_model, outputs=selected_model)
                refresh_models_btn.click(get_models_items, None, models_gallery)
                demo.load(fn=get_gallery_items, inputs=None, outputs=works_gallery)
                demo.load(fn=get_models_items, inputs=None, outputs=models_gallery)
                def start_training(video_file, model_name, request: gr.Request):
                    return self.train_model(video_file, model_name, require_username(request))

                train_btn.click(
                    fn=start_training,
                    inputs=[video_input, model_name],
                    outputs=[train_output]
                )
                def generate_video(video_path, text, request: gr.Request):
                    if not video_path:
                        return "错误: 请先选择数字人模特", None
                    if not text:
                        return "错误: 请输入要合成的文本", None

                    username = require_username(request)
                    try:
                        model_path = self.resolve_model_path(video_path, username)
                        model_result = self.get_model_training_result(model_path.stem, username)
                        if not model_result:
                            return "错误: 未找到模型训练结果", None

                        audio_path = self.audio_service.synthesize_audio(
                            text=text,
                            reference_text=model_result.get("reference_audio_text", ""),
                            reference_audio=model_result.get("asr_format_audio_url", ""),
                            username=username,
                        )

                        task_id = self.video_service.make_video(
                            video_path=model_path,
                            audio_path=Path(audio_path),
                            username=username,
                        )
                        self.record_video_task_owner(task_id, username)

                        return "视频任务已提交。请点击“检查状态”查询进度。", task_id
                    except Exception as e:
                        logger.error(f"生成视频失败: {str(e)}")
                        return f"生成视频失败: {str(e)}", None

                def check_status(task_id, request: gr.Request):
                    if not task_id:
                        return "请先生成视频获取任务ID"

                    username = require_username(request)
                    with self.video_task_lock:
                        owner = self.video_task_owners.get(task_id)
                    if owner != username:
                        return f"未找到任务: {task_id}"

                    try:
                        status_data = self.video_service.check_status(task_id)
                        if status_data.get("code") != 10000 or status_data.get("success") is False:
                            return f"状态查询失败: {status_data}"

                        data = status_data.get("data", {})
                        status = data.get("status")
                        status_kind = classify_video_status(status)
                        if status_kind == "processing":
                            return f"⏳ 处理中，进度: {data.get('progress', 0)}%"
                        if status_kind == "completed":
                            success, message, _ = self._move_video_to_user_dir(data.get("result", ""), username)
                            if success:
                                self._cleanup_temp_images(username)
                                return f"🎉 {message}"
                            return message
                        if status_kind == "failed":
                            return f"❌ 任务失败: {data.get('msg', 'unknown error')}"
                        return f"状态未知: {status_data}"
                    except Exception as e:
                        logger.error(f"状态检查失败: {str(e)}")
                        return f"状态检查失败: {str(e)}"
                
                generate_btn.click(
                    fn=generate_video,
                    inputs=[video_path_input, text_input],
                    outputs=[status_output, task_id_output]
                )
                check_status_btn.click(
                    fn=check_status,
                    inputs=[task_id_output],
                    outputs=[status_output]
                )

                def start_cleanup(days, request: gr.Request):
                    return self.cleanup_files(days, require_username(request))

                cleanup_btn.click(
                    fn=start_cleanup,
                    inputs=[days_input],
                    outputs=[cleanup_output]
                )

                # --- 帮助与反馈逻辑 ---
                def submit_feedback(feedback_type, content, email, request: gr.Request):
                    if not content:
                        return "❌ 请输入反馈内容"

                    username = require_username(request)
                    try:
                        logger.info("收到用户反馈: 类型=%s, 用户=%s", feedback_type, username)

                        feedback_dir = self.file_service.get_user_dir(username) / "feedback"
                        feedback_dir.mkdir(parents=True, exist_ok=True)

                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                        feedback_file = feedback_dir / f"feedback_{timestamp}.txt"

                        with open(feedback_file, "w", encoding="utf-8") as f:
                            f.write(f"类型: {feedback_type}\n")
                            f.write(f"时间: {datetime.now().isoformat()}\n")
                            f.write(f"用户: {username}\n")
                            if email:
                                f.write(f"邮箱: {email}\n")
                            f.write(f"内容:\n{content}\n")
                        
                        return "✅ 感谢您的反馈！我们会尽快处理。"
                    except Exception as e:
                        logger.error(f"保存反馈失败: {str(e)}")
                        return f"❌ 提交失败: {str(e)}"
                
                feedback_btn.click(
                    fn=submit_feedback,
                    inputs=[feedback_type, feedback_content, feedback_email],
                    outputs=feedback_status
                )
        return demo

    @staticmethod
    def _validate_model_name(model_name: str) -> str:
        model_name = str(model_name or "")
        if (
            not model_name
            or model_name != model_name.strip()
            or model_name in {".", ".."}
            or "/" in model_name
            or "\\" in model_name
            or "\x00" in model_name
            or len(model_name) > 100
        ):
            raise ValueError("模特名称不能为空，且不能包含路径字符或超过100个字符")
        return model_name

    def resolve_model_path(self, model_value, username: str) -> Path:
        """Resolve a selected model without allowing access outside its user directory."""
        user_dir = self.file_service.get_user_dir(username).resolve()
        raw_value = str(model_value or "")
        if not raw_value:
            raise ValueError("请选择数字人模特")

        candidate = Path(raw_value)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            if "/" in raw_value or "\\" in raw_value or candidate.name != raw_value:
                raise ValueError("模特路径不安全")
            filename = candidate.name if candidate.suffix else f"{candidate.name}.mp4"
            resolved = (user_dir / filename).resolve()

        if resolved.parent != user_dir or resolved.suffix.lower() != ".mp4":
            raise ValueError("模特路径不安全")
        if not resolved.is_file():
            raise ValueError(f"模特不存在: {resolved.name}")
        return resolved

    def train_model(self, video_file, model_name, username: str):
        """Create a background task that calls the configured TTS preprocessing API."""
        try:
            if not video_file:
                return "错误：请提供MP4视频文件"

            model_name = self._validate_model_name(model_name)
            user_dir = self.file_service.get_user_dir(username)
            model_path = user_dir / f"{model_name}.mp4"
            result_file = user_dir / f"{model_name}_training.json"
            if model_path.exists() or result_file.exists():
                return f"错误：模特名称已存在: {model_name}"

            uploaded_path = self.file_service.save_uploaded_file(
                video_file,
                Path(getattr(video_file, "name", video_file)).name,
                username,
            )
            params = {"video_path": str(uploaded_path), "model_name": model_name}

            def train_model_task(task):
                logger.info("开始训练语音参考数据: 用户=%s, 模特=%s", username, model_name)
                audio_path = self.file_service.get_audio_path(uploaded_path, username)
                if not self.audio_service.extract_audio(uploaded_path, audio_path):
                    raise RuntimeError("从视频中提取音频失败")

                training_result = self.audio_service.train_voice_model(audio_path)
                if not training_result:
                    raise RuntimeError("TTS预处理服务未返回训练结果")

                uploaded_path.rename(model_path)
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(training_result, f, ensure_ascii=False, indent=2)

                return {
                    "model_name": model_name,
                    "video_path": str(model_path),
                    "audio_path": str(audio_path),
                    "reference_audio": training_result.get("asr_format_audio_url"),
                    "reference_text": training_result.get("reference_audio_text"),
                }

            task_id = self.task_service.create_task(
                task_type=TaskType.MODEL_TRAINING,
                params=params,
                username=username,
                priority=TaskPriority.HIGH,
                callback=train_model_task,
            )
            return f"已创建训练任务，任务ID: {task_id}\n请在任务队列中查看结果。"
        except Exception as e:
            logger.error(f"训练模型失败: {str(e)}")
            return f"训练失败: {str(e)}"

    def get_uploaded_videos(self, username: str):
        return self.file_service.scan_uploaded_videos(username)

    def cleanup_files(self, days_old: int, username: str) -> str:
        """清理临时文件"""
        try:
            if days_old < 1:
                return "错误：清理天数必须大于等于1"
            
            # 创建文件清理任务
            params = {
                "days_old": days_old
            }
            
            def cleanup_files_task(task):
                logger.info("开始清理用户文件: 用户=%s, 天数=%s", username, days_old)
                result = self.file_service.cleanup_temp_files(days_old, username)
                self.task_service.update_task_progress(task.task_id, 50)
                return result
            
            task_id = self.task_service.create_task(
                task_type=TaskType.FILE_CLEANUP,
                params=params,
                username=username,
                priority=TaskPriority.LOW,
                callback=cleanup_files_task,
            )
            
            return f"已创建文件清理任务，任务ID: {task_id}\n请在任务队列中查看进度。"
            
        except Exception as e:
            logger.error(f"文件清理失败: {str(e)}")
            return f"文件清理失败: {str(e)}"

    def get_works(self, username: str):
        return self.file_service.scan_works(username)

    def get_works_info(self, username: str):
        works = []
        for file in self.file_service.scan_works(username):
            file_path = Path(file["path"]) if isinstance(file, dict) else Path(file)
            works.append({
                "name": file_path.stem,
                "path": str(file_path),
                "cover": None,
                "created_time": file_path.stat().st_ctime
            })
        return works

    def get_models_info(self, username: str):
        models = []
        for file in self.file_service.scan_models(username):
            file_path = Path(file["path"])
            models.append({
                "name": file_path.stem,
                "path": str(file_path),
                "cover": None
            })
        return models

    def get_model_training_result(self, model_name, username: str):
        try:
            model_name = self._validate_model_name(model_name)
            user_dir = self.file_service.get_user_dir(username)
            result_file = user_dir / f"{model_name}_training.json"
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"读取训练结果失败: {str(e)}")
            return None

def main():
    try:
        print("开始启动HeyGem Web界面...")
        logger.info("启动HeyGem Web界面")

        validate_auth_configuration()
        
        print("创建HeyGemApp实例...")
        app = HeyGemApp()
        
        print("创建Gradio界面...")
        demo = app.create_interface()
        
        print(f"启动Gradio服务器，地址: {SERVER_HOST}:{SERVER_PORT}")
        demo.launch(
            server_name=SERVER_HOST,
            server_port=SERVER_PORT,
            share=False,
            favicon_path=None,
            css=custom_css,
            auth=list(VALID_CREDENTIALS.items()),
            auth_message="请使用管理员在环境变量中配置的 HeyGemWeb 账号登录。",
        )
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        logger.error(f"程序启动失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # 确保停止任务队列服务
        if 'app' in locals() and hasattr(app, 'task_service'):
            app.task_service.stop()
            logger.info("任务队列服务已停止")

if __name__ == "__main__":
    main()
