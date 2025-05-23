import logging
import gradio as gr
import uuid
import os

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

/* 使用系统字体作为后备 */
body {
    font-family: 'System UI', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}
"""

class HeyGemApp:
    def __init__(self):
        self.audio_service = AudioService()
        self.video_service = VideoService()
        self.file_service = FileService()
        self.current_user = None
        self.is_logged_in = False

    def login(self, username, password):
        if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
            self.is_logged_in = True
            self.current_user = username
            return True, "登录成功"
        return False, "用户名或密码错误"

    def create_interface(self):
        with gr.Blocks(title="HeyGem数字人", css=custom_css) as demo:
            login_state = gr.State(value=False)
            current_user_state = gr.State(value=None)
            # 登录区
            with gr.Group(visible=True) as login_group:
                gr.Markdown("# HeyGem数字人登录")
                username = gr.Textbox(label="用户名", placeholder="请输入用户名")
                password = gr.Textbox(label="密码", placeholder="请输入密码", type="password")
                login_btn = gr.Button("登录")
                login_status = gr.Textbox(label="登录状态", interactive=False)
            # 主界面区
            with gr.Group(visible=False) as main_group:
                gr.Markdown("# HeyGem数字人界面")
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
                            check_status_btn = gr.Button("检查状态")
                            status_output = gr.Textbox(label="状态", lines=3)
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
                def generate_video(video_path, text, ref_audio, ref_text):
                    try:
                        if not video_path:
                            raise ValueError("请选择数字人模特")
                        video_path_full = str(self.file_service.get_user_dir(self.current_user) / f"{video_path}.mp4")
                        if not Path(video_path_full).exists():
                            raise ValueError(f"模特 {video_path_full} 不存在")
                        model_name = Path(video_path_full).stem
                        training_result = self.get_model_training_result(model_name)
                        if training_result:
                            self.audio_service.training_result = training_result
                        audio_path = self.audio_service.synthesize_audio(
                            text=text,
                            reference_audio=ref_audio,
                            reference_text=ref_text,
                            username=self.current_user
                        )
                        task_id = self.video_service.make_video(
                            video_path=Path(video_path_full),
                            audio_path=Path(audio_path),
                            username=self.current_user
                        )
                        return task_id, "", None, None
                    except Exception as e:
                        logger.error(f"生成过程中发生错误: {str(e)}")
                        return f"错误: {str(e)}", "", None, None
                def check_status_loop(task_id):
                    if not task_id:
                        return "", None, None
                    try:
                        status_data = self.video_service.check_status(task_id)
                        if status_data.get('code') == 10000:
                            data = status_data.get('data', {})
                            if data.get('status') == 1:
                                return f"进度: {data.get('progress')}%状态: 处理中", None, None
                            elif data.get('status') == 2:
                                video_path = data.get('result')
                                return f"状态: 已完成,视频保存位置: {video_path}", video_path, video_path
                            elif data.get('status') == 3:
                                return f"状态: 失败,错误: {data.get('msg')}", None, None
                        return f"状态: 未知,响应: {status_data}", None, None
                    except Exception as e:
                        logger.error(f"状态检查过程中发生错误: {str(e)}")
                        return f"状态检查过程中发生错误: {str(e)}", None, None
                generate_btn.click(
                    fn=generate_video,
                    inputs=[video_path_input, text_input, reference_audio, reference_text],
                    outputs=[task_id_output, status_output]
                )
                check_status_btn.click(
                    fn=check_status_loop,
                    inputs=[task_id_output],
                    outputs=[status_output]
                )
                cleanup_btn.click(
                    fn=lambda days: self.cleanup_files(days),
                    inputs=[days_input],
                    outputs=[cleanup_output]
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
        try:
            if video_file is None:
                return "错误: 请先上传视频文件"
            if not model_name:
                return "错误: 请输入模特名称"
            video_path = self.file_service.save_uploaded_file(video_file, video_file.name, self.current_user)
            # 提取音频
            audio_path = self.file_service.get_audio_path(video_path, self.current_user)
            if not self.audio_service.extract_audio(video_path, audio_path):
                return "错误: 从视频中提取音频失败"
            training_result = self.audio_service.train_voice_model(audio_path)
            if not training_result:
                return "错误: 语音模型训练失败"
            result_file = video_path.parent / f"{model_name}_training.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(training_result, f, ensure_ascii=False, indent=2)
            new_video_path = video_path.parent / f"{model_name}.mp4"
            video_path.rename(new_video_path)
            return f"""模型训练成功完成。\n模特名称: {model_name}\n视频保存位置: {new_video_path}\n音频保存位置: {audio_path}\n参考音频: {training_result.get('asr_format_audio_url')}\n参考文本: {training_result.get('reference_audio_text')}"""
        except ValueError as e:
            logger.warning(f"验证错误: {str(e)}")
            return f"错误: {str(e)}"
        except Exception as e:
            logger.error(f"训练过程中发生意外错误: {str(e)}")
            return f"训练过程中发生错误: {str(e)}"

    def get_uploaded_videos(self):
        return self.file_service.scan_uploaded_videos(self.current_user)

    def synthesize_audio(self, text, reference_text, reference_audio, username=None):
        try:
            audio_path = self.audio_service.synthesize_audio(text, reference_text, reference_audio, username or self.current_user)
            return f"音频合成成功。\n音频保存位置: {audio_path}"
        except ValueError as e:
            logger.warning(f"验证错误: {str(e)}")
            return f"错误: {str(e)}"
        except Exception as e:
            logger.error(f"音频合成过程中发生意外错误: {str(e)}")
            return f"音频合成过程中发生错误: {str(e)}"

    def make_video(self, video_path, audio_path):
        try:
            task_id = self.video_service.make_video(
                Path(video_path),
                Path(audio_path),
                username=self.current_user
            )
            return task_id
        except Exception as e:
            logger.error(f"视频生成过程中发生意外错误: {str(e)}")
            return f"视频生成过程中发生错误: {str(e)}"

    def cleanup_files(self, days_old: int) -> str:
        try:
            result = self.file_service.cleanup_temp_files(days_old, self.current_user)
            output = "清理完成:\n"
            for dir_name, stats in result.items():
                output += f"\n{dir_name}:\n"
                output += f"  成功删除: {stats['deleted']} 个文件\n"
                output += f"  删除失败: {stats['failed']} 个文件\n"
            return output
        except Exception as e:
            logger.error(f"清理过程中发生错误: {str(e)}")
            return f"清理过程中发生错误: {str(e)}"

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
    """主函数"""
    logger.info("启动HeyGem Web界面")
    app = HeyGemApp()
    demo = app.create_interface()
    demo.launch(
        server_name=SERVER_HOST,
        server_port=SERVER_PORT,
        share=True,
        allowed_paths=[
            "/root/heygem_data",  # 添加数据目录
            "/home/HeyGemWeb",    # 当前工作目录
            "/tmp"                # 系统临时目录
        ]
    )

if __name__ == "__main__":
    main()