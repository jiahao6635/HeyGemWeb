import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.video_service import VideoService


class VideoServiceTest(unittest.TestCase):
    def _media_files(self, temp_dir):
        video_path = Path(temp_dir) / "model.mp4"
        audio_path = Path(temp_dir) / "audio.wav"
        video_path.write_bytes(b"video")
        audio_path.write_bytes(b"audio")
        return video_path, audio_path

    def test_submission_validates_business_response(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 10001, "success": False, "msg": "busy"}

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path, audio_path = self._media_files(temp_dir)
            with patch("services.video_service.requests.post", return_value=response):
                with self.assertRaisesRegex(RuntimeError, "busy"):
                    VideoService().make_video(video_path, audio_path, username="alice")

    def test_submission_uses_generated_task_id_and_timeout(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 10000, "success": True, "data": {}}

        with tempfile.TemporaryDirectory() as temp_dir:
            video_path, audio_path = self._media_files(temp_dir)
            with (
                patch("services.video_service.uuid.uuid4", return_value="task-123"),
                patch("services.video_service.requests.post", return_value=response) as post,
            ):
                task_id = VideoService().make_video(video_path, audio_path, username="alice")

        self.assertEqual(task_id, "task-123")
        self.assertEqual(post.call_args.kwargs["json"]["code"], "task-123")
        self.assertEqual(post.call_args.kwargs["json"]["video_url"], "alice/model.mp4")
        self.assertEqual(post.call_args.kwargs["timeout"], (5, 60))

    def test_completed_status_requires_non_empty_mp4_result(self):
        service = VideoService()
        with patch.object(
            service,
            "check_status",
            return_value={"code": 10000, "data": {"status": 2, "result": ""}},
        ):
            with self.assertRaises(ValueError):
                service.get_video_path("task-123", username="alice")

    def test_completed_status_normalizes_windows_result_path(self):
        service = VideoService()
        with patch.object(
            service,
            "check_status",
            return_value={
                "code": 10000,
                "data": {"status": 2, "result": r"D:\\heygem\\result\\video.mp4"},
            },
        ):
            result = service.get_video_path("task-123", username="alice")

        self.assertEqual(result.name, "video.mp4")

    def test_status_query_uses_timeout(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": 10000,
            "success": True,
            "data": {"status": 1, "progress": 10},
        }

        with patch("services.video_service.requests.get", return_value=response) as get:
            payload = VideoService().check_status("task-123")

        self.assertEqual(payload["data"]["progress"], 10)
        self.assertEqual(get.call_args.kwargs["timeout"], (5, 60))


if __name__ == "__main__":
    unittest.main()
