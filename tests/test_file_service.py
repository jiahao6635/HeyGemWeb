import os
import shutil
import tempfile
import unittest
from pathlib import Path


TEST_DATA_ROOT = Path(tempfile.mkdtemp(prefix="heygemweb-tests-"))
os.environ["HEYGEM_BASE_DIR"] = str(TEST_DATA_ROOT / "runtime")

from config import MAX_CONTENT_LENGTH  # noqa: E402
from services.file_service import FileService  # noqa: E402


class FileServiceTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_DATA_ROOT, ignore_errors=True)

    def setUp(self):
        self.case_dir = Path(tempfile.mkdtemp(dir=TEST_DATA_ROOT))
        self.service = FileService(
            upload_dir=self.case_dir / "uploads",
            tts_train_dir=self.case_dir / "voice",
            tts_product_dir=self.case_dir / "processed",
        )

    def tearDown(self):
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def test_accepts_only_mp4_extensions(self):
        self.assertTrue(self.service.check_file_extension("avatar.mp4"))
        self.assertTrue(self.service.check_file_extension("avatar.MP4"))
        self.assertFalse(self.service.check_file_extension("avatar.mov"))
        self.assertFalse(self.service.check_file_extension("avatar.mp4.exe"))

    def test_upload_size_boundary(self):
        self.assertTrue(self.service.check_file_size(MAX_CONTENT_LENGTH))
        self.assertFalse(self.service.check_file_size(MAX_CONTENT_LENGTH + 1))

    def test_saves_gradio_filepath_string(self):
        source = self.case_dir / "source.mp4"
        source.write_bytes(b"video")

        saved = self.service.save_uploaded_file(str(source), source.name, "alice")

        self.assertEqual(saved.read_bytes(), b"video")
        self.assertEqual(saved.parent, (self.case_dir / "uploads" / "alice").resolve())

    def test_creates_isolated_user_directories(self):
        user_dir = self.service.get_user_dir("alice")
        tts_dir = self.service.get_user_tts_dir("alice")
        product_dir = self.service.get_user_tts_product_dir("alice")

        self.assertEqual(user_dir, (self.case_dir / "uploads" / "alice").resolve())
        self.assertEqual(tts_dir, (self.case_dir / "voice" / "alice").resolve())
        self.assertEqual(product_dir, (self.case_dir / "processed" / "alice").resolve())
        self.assertTrue(user_dir.is_dir())
        self.assertTrue(tts_dir.is_dir())
        self.assertTrue(product_dir.is_dir())

    def test_rejects_user_directory_traversal(self):
        for username in ("", "..", "../outside", "nested/user", "nested\\user"):
            with self.subTest(username=username):
                with self.assertRaises(ValueError):
                    self.service.get_user_dir(username)


if __name__ == "__main__":
    unittest.main()
