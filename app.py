import logging
import gradio as gr
import uuid
from pathlib import Path
from config import (
    SERVER_HOST,
    SERVER_PORT,
    LOG_FILE,
    LOG_LEVEL,
    LOG_DIR
)
from services.audio_service import AudioService
from services.video_service import VideoService
from services.file_service import FileService
import mimetypes
from datetime import datetime

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

custom_css = """
/* 隐藏 Gradio 页脚 */
footer, .svelte-1ipelgc, .svelte-1ipelgc * { display: none !important; }
/* 隐藏 Gradio 顶部Logo和标题栏 */
#logo, .prose, .gradio-container .prose, .gradio-container .svelte-1ipelgc { display: none !important; }
/* 隐藏加载动画 */
#loading, .loading, .svelte-1ipelgc .loading { display: none !important; }
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
}
"""

class HeyGemApp:
    def __init__(self):
        self.audio_service = AudioService()
        self.video_service = VideoService()
        self.file_service = FileService()
        # 初始化时扫描已上传的视频
        self.uploaded_videos = self.file_service.scan_uploaded_videos()
        logger.info(f"Initialized with {len(self.uploaded_videos)} uploaded videos")

    def train_model(self, video_file, model_name):
        """训练模特模型"""
        try:
            if video_file is None:
                return "错误: 请先上传视频文件"
            
            if not model_name:
                return "错误: 请输入模特名称"
                
            # 保存视频文件
            video_path = self.file_service.save_uploaded_file(video_file, video_file.name)
            self.uploaded_videos.append(str(video_path.name))  # 添加到已上传视频列表
            
            # 提取音频
            audio_path = self.file_service.get_audio_path(video_path)
            if not self.audio_service.extract_audio(video_path, audio_path):
                return "错误: 从视频中提取音频失败"
            
            # 训练语音模型
            training_result = self.audio_service.train_voice_model(audio_path)
            if not training_result:
                return "错误: 语音模型训练失败"
            
            # 重命名视频文件为模特名称
            new_video_path = video_path.parent / f"{model_name}.mp4"
            video_path.rename(new_video_path)
            
            return f"""模型训练成功完成。
            模特名称: {model_name}
            视频保存位置: {new_video_path}
            音频保存位置: {audio_path}
            参考音频: {training_result.get('asr_format_audio_url')}
            参考文本: {training_result.get('reference_audio_text')}"""
        except ValueError as e:
            logger.warning(f"验证错误: {str(e)}")
            return f"错误: {str(e)}"
        except Exception as e:
            logger.error(f"训练过程中发生意外错误: {str(e)}")
            return f"训练过程中发生错误: {str(e)}"

    def get_uploaded_videos(self):
        """获取已上传的视频列表"""
        # 每次获取时重新扫描目录，确保列表是最新的
        self.uploaded_videos = self.file_service.scan_uploaded_videos()
        return self.uploaded_videos

    def synthesize_audio(self, text, reference_text, reference_audio):
        """合成音频"""
        try:
            audio_path = self.audio_service.synthesize_audio(text, reference_text, reference_audio)
            return f"音频合成成功。\n音频保存位置: {audio_path}"
        except ValueError as e:
            logger.warning(f"验证错误: {str(e)}")
            return f"错误: {str(e)}"
        except Exception as e:
            logger.error(f"音频合成过程中发生意外错误: {str(e)}")
            return f"音频合成过程中发生错误: {str(e)}"

    def make_video(self, video_path, audio_path):
        """生成视频"""
        try:
            task_id = self.video_service.make_video(
                Path(video_path),
                Path(audio_path)
            )
            return task_id
        except Exception as e:
            logger.error(f"视频生成过程中发生意外错误: {str(e)}")
            return f"视频生成过程中发生错误: {str(e)}"

    def check_status(self, task_id):
        """检查视频生成状态"""
        try:
            status_data = self.video_service.check_status(task_id)
            
            if status_data.get('code') == 10000:
                data = status_data.get('data', {})
                if data.get('status') == 1:
                    return f"进度: {data.get('progress')}%\n状态: 处理中", None, None
                elif data.get('status') == 2:
                    video_path = data.get('result')
                    return f"状态: 已完成\n视频保存位置: {video_path}", video_path, video_path
                elif data.get('status') == 3:
                    return f"状态: 失败\n错误: {data.get('msg')}", None, None
            return f"状态: 未知\n响应: {status_data}", None, None
        except ValueError as e:
            logger.warning(f"验证错误: {str(e)}")
            return f"错误: {str(e)}", None, None
        except Exception as e:
            logger.error(f"状态检查过程中发生意外错误: {str(e)}")
            return f"状态检查过程中发生错误: {str(e)}", None, None

    def cleanup_files(self, days_old: int) -> str:
        """清理临时文件"""
        try:
            result = self.file_service.cleanup_temp_files(days_old)
            
            # 格式化输出结果
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
        """获取所有作品列表（以 -r.mp4 结尾）"""
        return self.file_service.scan_works()

    def get_works_info(self):
        """获取所有作品信息（视频名称、路径、封面）"""
        works = []
        for file in self.file_service.scan_works():
            # 兼容 file 可能为 dict 或 str
            file_path = Path(file["path"]) if isinstance(file, dict) else Path(file)
            works.append({
                "name": file_path.stem,
                "path": str(file_path),
                "cover": None,  # 可扩展为缩略图
                "created_time": file_path.stat().st_ctime
            })
        return works

    def get_models_info(self):
        """获取所有模特模型信息"""
        models = []
        for file in self.file_service.scan_models():
            # 兼容 file 可能为 dict 或 str
            file_path = Path(file["path"]) if isinstance(file, dict) else Path(file)
            models.append({
                "name": file_path.stem,
                "path": str(file_path),
                "cover": None,  # 可扩展为缩略图
                "created_time": file_path.stat().st_ctime
            })
        return models

    def create_interface(self):
        """创建Gradio界面"""
        with gr.Blocks(title="HeyGem数字人", css=custom_css) as demo:
            gr.Markdown("# HeyGem数字人界面")
            
            with gr.Tab("我的作品"):
                with gr.Row():
                    with gr.Column(scale=1):
                        works_gallery = gr.Gallery(
                            label="我的作品",
                            show_label=True,
                            elem_id="works_gallery",
                            columns=3,
                            allow_preview=True,
                            height=600,  # 增加高度以显示更多内容
                            object_fit="contain",
                            show_download_button=True,
                            container=True
                        )
                with gr.Row():
                    refresh_btn = gr.Button("刷新作品列表")
                    selected_video = gr.State(value=None)   
                    download_btn = gr.Button("下载选中视频")

            with gr.Tab("我的数字模特"):
                with gr.Row():
                    with gr.Column(scale=1):
                        models_gallery = gr.Gallery(
                            label="我的数字模特",
                            show_label=True,
                            elem_id="models_gallery",
                            columns=3,
                            allow_preview=True,
                            height=600,  # 增加高度以显示更多内容
                            object_fit="contain",
                            show_download_button=True,
                            container=True
                        )
                with gr.Row():
                    refresh_models_btn = gr.Button("刷新模特列表")
                    selected_model = gr.State(value=None)
                    download_model_btn = gr.Button("下载选中模特")

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
                        video_path_input = gr.Dropdown(
                            label="选择数字人模特",
                            choices=[],  # 初始化为空列表
                            allow_custom_value=True,
                            value=None  # 添加默认值
                        )
                        text_input = gr.Textbox(label="要合成的文本", lines=3)
                        generate_btn = gr.Button("生成视频")
                        task_id_output = gr.Textbox(label="任务ID")
            
            with gr.Tab("状态检查"):
                with gr.Row():
                    with gr.Column():
                        task_id_input = gr.Textbox(label="任务ID")
                        check_btn = gr.Button("检查状态")
                        status_output = gr.Textbox(label="状态", lines=3)
                        video_preview = gr.Video(label="视频预览")
                        video_download = gr.File(label="下载视频")
            
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
                works = self.get_works_info()
                # 只传视频路径和标题，便于视频预览
                return [
                    (w["path"], f"{w['name']}\n创建时间: {datetime.fromtimestamp(w['created_time']).strftime('%Y-%m-%d %H:%M:%S')}")
                    for w in works
                ]

            def get_models_items():
                models = self.get_models_info()
                return [
                    (m["path"], f"{m['name']}\n创建时间: {datetime.fromtimestamp(m['created_time']).strftime('%Y-%m-%d %H:%M:%S')}")
                    for m in models
                ]

            def get_models_dropdown():
                models = self.get_models_info()
                # 只返回文件名字符串列表
                return [m["name"] for m in models]

            def select_video(evt: gr.SelectData):
                works = self.get_works_info()
                selected = works[evt.index]
                return selected["path"]

            def select_model(evt: gr.SelectData):
                models = self.get_models_info()
                selected = models[evt.index]
                return selected["path"]

            def download_selected_video(video_path):
                if video_path and Path(video_path).exists():
                    return str(video_path)
                return None

            def download_selected_model(model_path):
                if model_path and Path(model_path).exists():
                    return str(model_path)
                return None

            # 作品相关事件
            works_gallery.select(select_video, outputs=selected_video)
            download_btn.click(download_selected_video, inputs=selected_video, outputs=None)

            # 模特相关事件
            models_gallery.select(select_model, outputs=selected_model)
            download_model_btn.click(download_selected_model, inputs=selected_model, outputs=None)

            # 初始化下拉框选项
            demo.load(get_models_dropdown, None, video_path_input)

            # 训练相关事件
            def on_training_complete(result):
                if "参考音频:" in result and "参考文本:" in result:
                    ref_audio = result.split("参考音频:")[1].split("\n")[0].strip()
                    ref_text = result.split("参考文本:")[1].strip()
                    return result, ref_audio, ref_text
                return result, "", ""
            
            train_btn.click(
                fn=self.train_model,
                inputs=[video_input, model_name],
                outputs=[train_output]
            ).then(
                fn=on_training_complete,
                inputs=[train_output],
                outputs=[train_output, reference_audio, reference_text]
            ).then(
                fn=get_models_dropdown,  # 使用新的函数更新下拉框
                outputs=[video_path_input]
            ).then(
                fn=get_models_items,
                inputs=None,
                outputs=models_gallery
            )
            
            def generate_video(video_path, text, ref_audio, ref_text):
                try:
                    if not video_path:
                        raise ValueError("请选择数字人模特")
                        
                    audio_path = self.audio_service.synthesize_audio(
                        text=text,
                        reference_audio=ref_audio,
                        reference_text=ref_text
                    )
                    task_id = self.video_service.make_video(
                        video_path=Path(video_path),
                        audio_path=Path(audio_path)
                    )
                    return f"任务ID: {task_id}"
                except Exception as e:
                    logger.error(f"生成过程中发生错误: {str(e)}")
                    return f"错误: {str(e)}"
            
            generate_btn.click(
                fn=generate_video,
                inputs=[video_path_input, text_input, reference_audio, reference_text],
                outputs=[task_id_output]
            )
            
            check_btn.click(
                fn=self.check_status,
                inputs=[task_id_input],
                outputs=[status_output, video_preview, video_download]
            )
            
            cleanup_btn.click(
                fn=self.cleanup_files,
                inputs=[days_input],
                outputs=[cleanup_output]
            )
            
            return demo

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