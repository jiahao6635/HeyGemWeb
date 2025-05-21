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
            training_result = self.audio_service.train_voice_model(audio_path)
            if not training_result:
                return "Error: Failed to train voice model"
            
            # 保存训练结果供后续使用
            self.audio_service.save_training_result(training_result)
            
            return f"""Model training completed successfully.
Video saved at: {video_path}
Audio saved at: {audio_path}
Reference Audio: {training_result.get('asr_format_audio_url')}
Reference Text: {training_result.get('reference_audio_text')}"""
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return f"Error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during training: {str(e)}")
            return f"Error during training: {str(e)}"

    def synthesize_audio(self, voice_id, text, reference_text, reference_audio):
        """合成音频"""
        try:
            audio_path = self.audio_service.synthesize_audio(voice_id, text, reference_text, reference_audio)
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
                        train_output = gr.Textbox(label="Training Status", lines=5)
                        reference_audio = gr.Textbox(label="Reference Audio URL", visible=False)
                        reference_text = gr.Textbox(label="Reference Text", visible=False)
            
            with gr.Tab("Video Generation"):
                with gr.Row():
                    with gr.Column():
                        voice_id_input = gr.Textbox(label="Voice ID (UUID)")
                        video_path_input = gr.Textbox(label="Video Path")
                        text_input = gr.Textbox(label="Text to Synthesize", lines=3)
                        with gr.Row():
                            preview_btn = gr.Button("Preview Audio")
                            generate_btn = gr.Button("Generate Video")
                        audio_preview = gr.Audio(label="Audio Preview", type="filepath")
                        task_id_output = gr.Textbox(label="Task ID")
            
            with gr.Tab("Status Check"):
                with gr.Row():
                    with gr.Column():
                        task_id_input = gr.Textbox(label="Task ID")
                        check_btn = gr.Button("Check Status")
                        status_output = gr.Textbox(label="Status", lines=3)
            
            # Set up event handlers
            def on_training_complete(result):
                # 解析训练结果，提取reference_audio和reference_text
                if "Reference Audio:" in result and "Reference Text:" in result:
                    ref_audio = result.split("Reference Audio:")[1].split("\n")[0].strip()
                    ref_text = result.split("Reference Text:")[1].strip()
                    return result, ref_audio, ref_text
                return result, "", ""
            
            train_btn.click(
                fn=self.train_model,
                inputs=[video_input],
                outputs=[train_output]
            ).then(
                fn=on_training_complete,
                inputs=[train_output],
                outputs=[train_output, reference_audio, reference_text]
            )
            
            def preview_and_generate(voice_id, video_path, text, ref_audio, ref_text, generate_video=False):
                try:
                    if not voice_id:
                        voice_id = str(uuid.uuid4())
                    
                    # 合成音频
                    audio_path = self.audio_service.synthesize_audio(
                        voice_id=voice_id,
                        text=text,
                        reference_audio=ref_audio,
                        reference_text=ref_text
                    )
                    
                    if generate_video:
                        # 生成视频
                        task_id = self.video_service.make_video(
                            video_path=Path(video_path),
                            audio_path=Path(audio_path)
                        )
                        return audio_path, f"Task ID: {task_id}"
                    else:
                        return audio_path, "Audio preview ready"
                except Exception as e:
                    logger.error(f"Error in preview_and_generate: {str(e)}")
                    return None, f"Error: {str(e)}"
            
            preview_btn.click(
                fn=lambda v, p, t, ra, rt: preview_and_generate(v, p, t, ra, rt, False),
                inputs=[voice_id_input, video_path_input, text_input, reference_audio, reference_text],
                outputs=[audio_preview, task_id_output]
            )
            
            generate_btn.click(
                fn=lambda v, p, t, ra, rt: preview_and_generate(v, p, t, ra, rt, True),
                inputs=[voice_id_input, video_path_input, text_input, reference_audio, reference_text],
                outputs=[audio_preview, task_id_output]
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