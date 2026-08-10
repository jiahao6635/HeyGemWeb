import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from services.audio_service import AudioService


class AudioServiceTest(unittest.TestCase):
    def test_training_requires_reference_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "voice" / "data"
            training_dir = root / "origin_audio"
            audio_path = training_dir / "alice" / "reference.wav"
            audio_path.parent.mkdir(parents=True)
            audio_path.write_bytes(b"audio")

            response = Mock()
            response.raise_for_status.return_value = None
            response.json.return_value = {"code": 10000}

            with (
                patch("services.audio_service.TTS_TRAIN_DIR", training_dir),
                patch("services.audio_service.requests.post", return_value=response) as post,
            ):
                with self.assertRaises(ValueError):
                    AudioService().train_voice_model(audio_path)

            self.assertEqual(post.call_args.kwargs["timeout"], (5, 120))

    def test_synthesis_requires_explicit_model_reference(self):
        with patch("services.audio_service.requests.post") as post:
            with self.assertRaises(ValueError):
                AudioService().synthesize_audio(
                    text="hello",
                    reference_audio="",
                    reference_text="",
                    username="alice",
                )
        post.assert_not_called()

    def test_synthesis_rejects_non_wav_success_response(self):
        response = Mock()
        response.raise_for_status.return_value = None
        response.content = b'{"code": 10001, "msg": "busy"}'

        with patch("services.audio_service.requests.post", return_value=response):
            with self.assertRaises(ValueError):
                AudioService().synthesize_audio(
                    text="hello",
                    reference_audio="origin_audio/alice/reference.wav",
                    reference_text="reference",
                    username="alice",
                )

    def test_synthesis_saves_valid_wav_in_user_namespace(self):
        wav = b"RIFF" + (b"\x00" * 4) + b"WAVE" + b"payload"
        response = Mock()
        response.raise_for_status.return_value = None
        response.content = wav

        with tempfile.TemporaryDirectory() as temp_dir:
            upload_dir = Path(temp_dir) / "uploads"
            with (
                patch("services.audio_service.UPLOAD_DIR", upload_dir),
                patch("services.audio_service.requests.post", return_value=response),
            ):
                result = AudioService().synthesize_audio(
                    text="hello",
                    reference_audio="origin_audio/alice/reference.wav",
                    reference_text="reference",
                    username="alice",
                )

            result_path = Path(result)
            self.assertEqual(result_path.parent.resolve(), (upload_dir / "alice").resolve())
            self.assertEqual(result_path.read_bytes(), wav)


if __name__ == "__main__":
    unittest.main()
