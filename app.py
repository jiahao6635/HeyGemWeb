from dotenv import load_dotenv
load_dotenv()

import logging
import gradio as gr
import uuid
import os
import time

from pathlib import Path
from config import (
    SERVER_HOST,
    SERVER_PORT,
    LOG_FILE,
    LOG_LEVEL,
    LOG_DIR,
    UPLOAD_DIR
)
from services.audio_service import AudioService
from services.video_service import VideoService
from services.file_service import FileService
from services.task_service import TaskService, TaskType, TaskPriority, TaskStatus
import mimetypes
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

# 从环境变量获取用户凭据

VALID_CREDENTIALS = {}
for i in range(1, 11):  # 支持最多10个用户
    username = os.getenv(f'USER_{i}_NAME')
    password = os.getenv(f'USER_{i}_PASSWORD')
    print(f"用户{i}：{username}")
    if username and password:
        VALID_CREDENTIALS[username] = password

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
        self.current_user = None
        self.is_logged_in = False
        
        # 启动任务队列服务
        self.task_service.start()

    def login(self, username, password):
        if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
            self.is_logged_in = True
            self.current_user = username
            return True, "登录成功"
        return False, "用户名或密码错误"

    def _move_video_to_user_dir(self, video_filename):
        """移动视频文件到用户目录"""
        try:
            # 如果video_filename是完整路径，只取文件名部分
            if video_filename.startswith('/'):
                video_filename = Path(video_filename).name
                
            source_path = UPLOAD_DIR / video_filename
            logger.info(f"UPLOAD_DIR: {UPLOAD_DIR}")
            logger.info(f"video_filename: {video_filename}")
            logger.info(f"完整源文件路径: {source_path}")
            logger.info(f"源文件是否存在: {source_path.exists()}")
            
            if not source_path.exists():
                return False, f"视频文件不存在: {source_path}", None
                
            user_dir = self.file_service.get_user_dir(self.current_user)
            target_path = user_dir / video_filename
            source_path.rename(target_path)
            return True, f"视频已保存到: {target_path}", target_path
            
        except Exception as e:
            logger.error(f"移动视频文件失败: {str(e)}")
            return False, f"移动视频文件失败: {str(e)}", None

    def _cleanup_temp_images(self):
        """清理临时图片文件"""
        try:
            cleaned_files = []
            for temp_file in UPLOAD_DIR.glob("*.png"):
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
        with gr.Blocks(title="HeyGem数字人", css=custom_css) as demo:
            login_state = gr.State(value=False)
            current_user_state = gr.State(value=None)
            theme_state = gr.State(value="light")
            # 登录区
            with gr.Group(visible=True) as login_group:
                gr.Markdown("# HeyGem数字人登录")
                username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                password = gr.Textbox(label="密码", placeholder="请输入密码", type="password")
                login_btn = gr.Button("登录")
                login_status = gr.Textbox(label="登录状态", interactive=False)
            # 主界面区
            with gr.Group(visible=False) as main_group:
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
                            video_input = gr.File(label="上传视频")
                            model_name = gr.Textbox(label="模特名称", placeholder="请输入模特名称")
                            train_btn = gr.Button("开始训练")
                            train_output = gr.Textbox(label="训练状态", lines=5)
                            reference_audio = gr.Textbox(label="参考音频URL", visible=False)
                            reference_text = gr.Textbox(label="参考文本", visible=False)
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
                            
                            # 添加进度条
                            with gr.Row():
                                progress_bar = gr.Progress(label="任务进度", show_progress=True)
                                auto_refresh = gr.Checkbox(label="自动刷新状态", value=True)
                            
                            check_status_btn = gr.Button("检查状态")
                            status_output = gr.Textbox(label="状态", lines=3)
                            
                            # 添加操作引导
                            gr.Markdown("""
                            ### 操作指南
                            1. 输入模特名称（在"我的数字模特"中可以查看）
                            2. 输入要合成的文本
                            3. 点击"生成视频"按钮开始任务
                            4. 系统会自动更新进度，也可以手动点击"检查状态"
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
                            - 设置最大并发任务数
                            
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
                            
                            gr.Markdown("### 并发设置")
                            with gr.Row():
                                concurrent_tasks = gr.Slider(
                                    label="最大并发任务数",
                                    minimum=1,
                                    maximum=10,
                                    step=1,
                                    value=2
                                )
                                set_concurrent_btn = gr.Button("设置")
                                
                        with gr.Column(scale=3):
                            gr.Markdown("### 我的任务")
                            user_tasks = gr.Dataframe(
                                headers=["任务ID", "类型", "状态", "进度", "创建时间", "操作"],
                                datatype=["str", "str", "str", "number", "str", "str"],
                                row_count=10,
                                col_count=(6, "fixed"),
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
                def get_queue_status():
                    return self.task_service.get_queue_status()
                
                def get_user_tasks():
                    if not self.current_user:
                        return []
                    
                    tasks = self.task_service.get_user_tasks(self.current_user)
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
                
                def get_task_details(task_id):
                    if not task_id:
                        return {"error": "请输入任务ID"}
                    
                    task = self.task_service.get_task(task_id)
                    if not task:
                        return {"error": "未找到任务"}
                    
                    return task
                
                def cancel_task(task_id):
                    if not task_id:
                        return {"error": "请输入任务ID"}
                    
                    success = self.task_service.cancel_task(task_id)
                    if success:
                        return {"success": f"已取消任务 {task_id}"}
                    else:
                        return {"error": f"无法取消任务 {task_id}"}
                
                def set_max_concurrent_tasks(count):
                    success = self.task_service.set_max_concurrent_tasks(int(count))
                    if success:
                        return {"success": f"已设置最大并发任务数为 {count}"}
                    else:
                        return {"error": "设置失败"}
                
                # 绑定任务队列相关事件
                refresh_queue_btn.click(get_queue_status, None, queue_status)
                refresh_tasks_btn.click(get_user_tasks, None, user_tasks)
                get_task_btn.click(get_task_details, task_id_input, task_details)
                cancel_task_btn.click(cancel_task, task_id_input, task_details)
                set_concurrent_btn.click(set_max_concurrent_tasks, concurrent_tasks, queue_status)
                
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
                    outputs=[theme_state],
                    _js="""
                    function toggleTheme(theme) {
                        if (theme === "light") {
                            document.documentElement.classList.add('dark-theme');
                            return "dark";
                        } else {
                            document.documentElement.classList.remove('dark-theme');
                            return "light";
                        }
                    }
                    """
                )
                
                # --- 我的作品逻辑 ---
                def get_gallery_items():
                    if not self.current_user:
                        return []
                    return [(w["path"], w["name"]) for w in self.get_works_info()]
                def get_models_items():
                    if not self.current_user:
                        return []
                    return [(m["path"], m["name"]) for m in self.get_models_info()]
                def select_video(evt: gr.SelectData):
                    works = self.get_works_info()
                    selected = works[evt.index]
                    return selected["path"]
                def select_model(evt: gr.SelectData):
                    models = self.get_models_info()
                    selected = models[evt.index]
                    return selected["path"]
                works_gallery.select(select_video, outputs=selected_video)
                refresh_btn.click(get_gallery_items, None, works_gallery)
                models_gallery.select(select_model, outputs=selected_model)
                refresh_models_btn.click(get_models_items, None, models_gallery)
                demo.load(fn=get_gallery_items, inputs=None, outputs=works_gallery)
                demo.load(fn=get_models_items, inputs=None, outputs=models_gallery)
                def on_training_complete(result):
                    if "参考音频:" in result and "参考文本:" in result:
                        ref_audio = result.split("参考音频:")[1].split("\n")[0].strip()
                        ref_text = result.split("参考文本:")[1].strip()
                        return result, ref_audio, ref_text
                    return result, "", ""
                train_btn.click(
                    fn=lambda video_file, model_name: self.train_model(video_file, model_name),
                    inputs=[video_input, model_name],
                    outputs=[train_output]
                ).then(
                    fn=on_training_complete,
                    inputs=[train_output],
                    outputs=[train_output, reference_audio, reference_text]
                ).then(
                    fn=get_models_items,
                    inputs=None,
                    outputs=models_gallery
                )
                def generate_video(video_path, text):
                    if not video_path:
                        return "错误: 请先选择数字人模特", None
                    if not text:
                        return "错误: 请输入要合成的文本", None
                    
                    try:
                        # 获取模型训练结果
                        model_result = self.get_model_training_result(video_path)
                        if not model_result:
                            return "错误: 未找到模型训练结果", None
                        
                        # 合成音频
                        audio_task_id, audio_msg = self.synthesize_audio(
                            text=text,
                            reference_text=model_result.get("reference_audio_text", ""),
                            reference_audio=model_result.get("asr_format_audio_url", "")
                        )
                        
                        if not audio_task_id:
                            return audio_msg, None
                        
                        return f"音频合成任务已创建，任务ID: {audio_task_id}\n请在任务队列中查看进度。", audio_task_id
                    except Exception as e:
                        logger.error(f"生成视频失败: {str(e)}")
                        return f"生成视频失败: {str(e)}", None

                def check_status(task_id):
                    if not task_id:
                        return "请先生成视频获取任务ID"
                    
                    task = self.task_service.get_task(task_id)
                    if not task:
                        return f"未找到任务: {task_id}"
                    
                    status = task["status"]
                    progress = task["progress"]
                    
                    # 更新进度条
                    if progress > 0:
                        progress_bar.update(progress / 100)
                    
                    if status == TaskStatus.COMPLETED:
                        result = task["result"]
                        if task["task_type"] == TaskType.AUDIO_SYNTHESIS:
                            # 音频合成完成，开始视频生成
                            audio_path = result.get("audio_path")
                            video_task_id, video_msg = self.make_video(
                                video_path=video_path_input.value,
                                audio_path=audio_path
                            )
                            return f"✅ 音频合成已完成，开始生成视频。\n视频任务ID: {video_task_id}"
                        elif task["task_type"] == TaskType.VIDEO_GENERATION:
                            # 视频生成完成
                            video_path = result.get("video_path")
                            return f"🎉 视频生成已完成！\n视频保存路径: {video_path}\n请在'我的作品'中查看。"
                    elif status == TaskStatus.FAILED:
                        return f"❌ 任务失败: {task['error']}\n请检查输入参数或联系管理员。"
                    elif status == TaskStatus.CANCELLED:
                        return "⚠️ 任务已取消"
                    else:
                        return f"⏳ 任务状态: {status}, 进度: {progress}%\n请耐心等待..."
                
                # 自动刷新状态
                def auto_refresh_status():
                    task_id = task_id_output.value
                    if task_id and auto_refresh.value:
                        status = check_status(task_id)
                        return status
                    return status_output.value
                
                # 每5秒自动刷新一次状态
                demo.load(fn=auto_refresh_status, inputs=None, outputs=status_output, every=5)
                
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
                cleanup_btn.click(
                    fn=lambda days: self.cleanup_files(days),
                    inputs=[days_input],
                    outputs=[cleanup_output]
                )

                # --- 帮助与反馈逻辑 ---
                def submit_feedback(feedback_type, content, email):
                    if not content:
                        return "❌ 请输入反馈内容"
                    
                    try:
                        # 记录反馈到日志
                        logger.info(f"用户反馈: 类型={feedback_type}, 邮箱={email}, 内容={content}")
                        
                        # 保存反馈到文件
                        feedback_dir = Path("feedback")
                        feedback_dir.mkdir(exist_ok=True)
                        
                        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                        feedback_file = feedback_dir / f"feedback_{timestamp}.txt"
                        
                        with open(feedback_file, "w", encoding="utf-8") as f:
                            f.write(f"类型: {feedback_type}\n")
                            f.write(f"时间: {datetime.now().isoformat()}\n")
                            f.write(f"用户: {self.current_user}\n")
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
            def on_login(username, password):
                success, msg = self.login(username, password)
                if success:
                    return True, gr.update(visible=False), gr.update(visible=True), username, "登录成功"
                # 登录失败，主界面不显示，提示错误
                return False, gr.update(visible=True), gr.update(visible=False), None, msg
            login_btn.click(
                fn=on_login,
                inputs=[username, password],
                outputs=[login_state, login_group, main_group, current_user_state, login_status]
            )
        return demo

    def train_model(self, video_file, model_name):
        """训练模型"""
        try:
            if not video_file or not model_name:
                return "错误：请提供视频文件和模特名称"
            
            # 保存上传的视频文件
            file_path = self.file_service.save_uploaded_file(video_file, video_file.name, self.current_user)
            
            # 创建训练任务
            params = {
                "video_path": str(file_path),
                "model_name": model_name
            }
            
            def train_model_task(task):
                # 这里是实际的训练逻辑
                # 在实际应用中，这里应该调用模型训练API
                logger.info(f"开始训练模型: {model_name}")
                time.sleep(5)  # 模拟训练过程
                
                # 返回训练结果
                return {
                    "model_name": model_name,
                    "reference_audio": f"https://example.com/audio/{model_name}.wav",
                    "reference_text": "这是一段参考文本，用于测试语音合成效果。"
                }
            
            task_id = self.task_service.create_task(
                task_type=TaskType.MODEL_TRAINING,
                params=params,
                username=self.current_user,
                priority=TaskPriority.HIGH,
                callback=train_model_task
            )
            
            return f"已创建训练任务，任务ID: {task_id}\n请在任务队列中查看进度。"
            
        except Exception as e:
            logger.error(f"训练模型失败: {str(e)}")
            return f"训练失败: {str(e)}"

    def get_uploaded_videos(self):
        return self.file_service.scan_uploaded_videos(self.current_user)

    def synthesize_audio(self, text, reference_text, reference_audio, username=None):
        """合成音频"""
        try:
            if not text:
                return None, "错误：请输入要合成的文本"
            
            # 创建音频合成任务
            params = {
                "text": text,
                "reference_text": reference_text,
                "reference_audio": reference_audio
            }
            
            def synthesize_audio_task(task):
                # 这里是实际的音频合成逻辑
                logger.info(f"开始合成音频，文本长度: {len(text)}")
                time.sleep(3)  # 模拟合成过程
                
                # 返回合成结果
                return {
                    "audio_path": f"/tmp/audio_{uuid.uuid4()}.wav",
                    "duration": len(text) * 0.1  # 模拟音频时长
                }
            
            task_id = self.task_service.create_task(
                task_type=TaskType.AUDIO_SYNTHESIS,
                params=params,
                username=username or self.current_user,
                priority=TaskPriority.NORMAL,
                callback=synthesize_audio_task
            )
            
            return task_id, f"已创建音频合成任务，任务ID: {task_id}"
            
        except Exception as e:
            logger.error(f"音频合成失败: {str(e)}")
            return None, f"音频合成失败: {str(e)}"

    def make_video(self, video_path, audio_path):
        """生成视频"""
        try:
            if not video_path or not audio_path:
                return None, "错误：请提供视频路径和音频路径"
            
            # 创建视频生成任务
            params = {
                "video_path": video_path,
                "audio_path": audio_path
            }
            
            def make_video_task(task):
                # 这里是实际的视频生成逻辑
                logger.info(f"开始生成视频: {video_path}")
                time.sleep(10)  # 模拟视频生成过程
                
                # 生成结果视频路径
                result_video = f"{video_path.rsplit('.', 1)[0]}-r.mp4"
                
                # 返回生成结果
                return {
                    "video_path": result_video
                }
            
            task_id = self.task_service.create_task(
                task_type=TaskType.VIDEO_GENERATION,
                params=params,
                username=self.current_user,
                priority=TaskPriority.NORMAL,
                callback=make_video_task
            )
            
            return task_id, f"已创建视频生成任务，任务ID: {task_id}"
            
        except Exception as e:
            logger.error(f"视频生成失败: {str(e)}")
            return None, f"视频生成失败: {str(e)}"

    def cleanup_files(self, days_old: int) -> str:
        """清理临时文件"""
        try:
            if days_old < 1:
                return "错误：清理天数必须大于等于1"
            
            # 创建文件清理任务
            params = {
                "days_old": days_old
            }
            
            def cleanup_files_task(task):
                # 这里是实际的文件清理逻辑
                logger.info(f"开始清理 {days_old} 天前的文件")
                
                # 调用文件服务的清理方法
                result = self.file_service.cleanup_temp_files(days_old, self.current_user)
                
                # 更新任务进度
                self.task_service.update_task_progress(task.task_id, 50)
                
                # 返回清理结果
                return result
            
            task_id = self.task_service.create_task(
                task_type=TaskType.FILE_CLEANUP,
                params=params,
                username=self.current_user,
                priority=TaskPriority.LOW,
                callback=cleanup_files_task
            )
            
            return f"已创建文件清理任务，任务ID: {task_id}\n请在任务队列中查看进度。"
            
        except Exception as e:
            logger.error(f"文件清理失败: {str(e)}")
            return f"文件清理失败: {str(e)}"

    def get_works(self):
        return self.file_service.scan_works(self.current_user)

    def get_works_info(self):
        if not self.current_user:
            return []
        works = []
        for file in self.file_service.scan_works(self.current_user):
            file_path = Path(file["path"]) if isinstance(file, dict) else Path(file)
            works.append({
                "name": file_path.stem,
                "path": str(file_path),
                "cover": None,
                "created_time": file_path.stat().st_ctime
            })
        return works

    def get_models_info(self):
        if not self.current_user:
            return []
        models = []
        for file in self.file_service.scan_models(self.current_user):
            file_path = Path(file["path"])
            models.append({
                "name": file_path.stem,
                "path": str(file_path),
                "cover": None
            })
        return models

    def get_model_training_result(self, model_name):
        try:
            user_dir = self.file_service.get_user_dir(self.current_user)
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
        logger.info("启动HeyGem Web界面")
        app = HeyGemApp()
        demo = app.create_interface()
        demo.launch(
            server_name=SERVER_HOST,
            server_port=SERVER_PORT,
            share=False,
            favicon_path=None
        )
    except Exception as e:
        logger.error(f"程序启动失败: {str(e)}")
    finally:
        # 确保停止任务队列服务
        if 'app' in locals() and hasattr(app, 'task_service'):
            app.task_service.stop()
            logger.info("任务队列服务已停止")

if __name__ == "__main__":
    main()