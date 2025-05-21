import logging
import gradio as gr
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
    print(f"Warning: Failed to configure logging to file: {e}")
    # 如果文件日志配置失败，使用控制台日志
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)

class HeyGemApp:
    def __init__(self):
        self.audio_service = AudioService()
        self.video_service = VideoService()
        self.file_service = FileService()

    def train_model(self, video_file):
        """训练模特模型"""
        try:
            if video_file is None:
                return "Error: Please upload a video file first"
                
            # 保存视频文件
            video_path = self.file_service.save_uploaded_file(video_file, video_file.name)
            
            # 提取音频
            audio_path = self.file_service.get_audio_path(video_path)
            if not self.audio_service.extract_audio(video_path, audio_path):
                return "Error: Failed to extract audio from video"
            
            # 训练语音模型
            voice_id = self.audio_service.train_voice_model(audio_path)
            
            return f"Model training completed successfully.\nVideo saved at: {video_path}\nVoice ID: {voice_id}"
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during training: {str(e)}")
            return f"Error during training: {str(e)}"

    def synthesize_audio(self, voice_id, text):
        """合成音频"""
        try:
            audio_path = self.audio_service.synthesize_audio(voice_id, text)
            return f"Audio synthesized successfully.\nAudio saved at: {audio_path}"
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during audio synthesis: {str(e)}")
            return f"Error during audio synthesis: {str(e)}"

    def make_video(self, video_path, audio_path):
        """生成视频"""
        try:
            task_id = self.video_service.make_video(
                Path(video_path),
                Path(audio_path)
            )
            return task_id
        except Exception as e:
            logger.error(f"Unexpected error during video generation: {str(e)}")
            return f"Error during video generation: {str(e)}"

    def check_status(self, task_id):
        """检查视频生成状态"""
        try:
            status_data = self.video_service.check_status(task_id)
            
            if status_data.get('code') == 10000:
                data = status_data.get('data', {})
                if data.get('status') == 1:
                    return f"Progress: {data.get('progress')}%\nStatus: Processing"
                elif data.get('status') == 2:
                    return f"Status: Completed\nVideo saved at: {data.get('result')}"
                elif data.get('status') == 3:
                    return f"Status: Failed\nError: {data.get('msg')}"
            return f"Status: Unknown\nResponse: {status_data}"
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during status check: {str(e)}")
            return f"Error checking status: {str(e)}"

    def create_interface(self):
        """创建Gradio界面"""
        with gr.Blocks(title="HeyGem Digital Human") as demo:
            gr.Markdown("# HeyGem Digital Human Interface")
            
            with gr.Tab("Model Training"):
                with gr.Row():
                    with gr.Column():
                        video_input = gr.File(label="Upload Video")
                        train_btn = gr.Button("Start Training")
                        train_output = gr.Textbox(label="Training Status", lines=3)
            
            with gr.Tab("Audio Synthesis"):
                with gr.Row():
                    with gr.Column():
                        voice_id_input = gr.Textbox(label="Voice ID")
                        text_input = gr.Textbox(label="Text to Synthesize", lines=3)
                        audio_btn = gr.Button("Synthesize Audio")
                        audio_output = gr.Textbox(label="Synthesis Status", lines=3)
            
            with gr.Tab("Video Generation"):
                with gr.Row():
                    with gr.Column():
                        video_path_input = gr.Textbox(label="Video Path")
                        audio_path_input = gr.Textbox(label="Audio Path")
                        generate_btn = gr.Button("Generate Video")
                        task_id_output = gr.Textbox(label="Task ID")
            
            with gr.Tab("Status Check"):
                with gr.Row():
                    with gr.Column():
                        task_id_input = gr.Textbox(label="Task ID")
                        check_btn = gr.Button("Check Status")
                        status_output = gr.Textbox(label="Status", lines=3)
            
            # Set up event handlers
            train_btn.click(
                fn=self.train_model,
                inputs=[video_input],
                outputs=[train_output]
            )
            
            audio_btn.click(
                fn=self.synthesize_audio,
                inputs=[voice_id_input, text_input],
                outputs=[audio_output]
            )
            
            generate_btn.click(
                fn=self.make_video,
                inputs=[video_path_input, audio_path_input],
                outputs=[task_id_output]
            )
            
            check_btn.click(
                fn=self.check_status,
                inputs=[task_id_input],
                outputs=[status_output]
            )
            
            return demo

def main():
    """主函数"""
    logger.info("Starting HeyGem Web Interface")
    app = HeyGemApp()
    demo = app.create_interface()
    demo.launch(
        server_name=SERVER_HOST,
        server_port=SERVER_PORT,
        share=True
    )

if __name__ == "__main__":
    main() 