import unittest
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

import gradio as gr

import app


class AuthenticationTest(unittest.TestCase):
    def setUp(self):
        self.original_credentials = app.VALID_CREDENTIALS.copy()

    def tearDown(self):
        app.VALID_CREDENTIALS.clear()
        app.VALID_CREDENTIALS.update(self.original_credentials)

    def test_loads_multiple_complete_accounts(self):
        credentials, errors = app.load_credentials(
            {
                "USER_1_NAME": "alice",
                "USER_1_PASSWORD": "alice-password",
                "USER_2_NAME": "bob",
                "USER_2_PASSWORD": "bob-password",
            }
        )

        self.assertEqual(
            credentials,
            {"alice": "alice-password", "bob": "bob-password"},
        )
        self.assertEqual(errors, [])

    def test_empty_environment_loads_no_accounts(self):
        credentials, errors = app.load_credentials({})

        self.assertEqual(credentials, {})
        self.assertEqual(errors, [])

    def test_rejects_partial_and_unsafe_accounts(self):
        credentials, errors = app.load_credentials(
            {
                "USER_1_NAME": "alice",
                "USER_2_NAME": "../bob",
                "USER_2_PASSWORD": "bob-password",
            }
        )

        self.assertEqual(credentials, {})
        self.assertEqual(len(errors), 2)

    def test_requires_authenticated_configured_username(self):
        app.VALID_CREDENTIALS.clear()
        app.VALID_CREDENTIALS["alice"] = "password"

        self.assertEqual(
            app.require_username(SimpleNamespace(username="alice")),
            "alice",
        )
        with self.assertRaises(gr.Error):
            app.require_username(SimpleNamespace(username="bob"))
        with self.assertRaises(gr.Error):
            app.require_username(SimpleNamespace(username=None))

    def test_task_lookup_enforces_ownership(self):
        alice_task = {"username": "alice", "task_id": "known"}
        application = app.HeyGemApp.__new__(app.HeyGemApp)
        application.task_service = SimpleNamespace(
            get_task=lambda task_id: alice_task if task_id == "known" else None
        )

        self.assertIs(application.get_owned_task("known", "alice"), alice_task)
        self.assertIsNone(application.get_owned_task("known", "bob"))
        self.assertIsNone(application.get_owned_task("missing", "alice"))

    def test_video_task_ownership_survives_restart(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "video_tasks.json"
            application = app.HeyGemApp.__new__(app.HeyGemApp)
            application.video_task_lock = threading.Lock()
            application.video_task_db_path = registry
            application.video_task_owners = {}

            application.record_video_task_owner("task-123", "alice")

            reloaded = app.HeyGemApp.__new__(app.HeyGemApp)
            reloaded.video_task_db_path = registry
            self.assertEqual(reloaded._load_video_task_owners(), {"task-123": "alice"})

    def test_video_status_accepts_both_failure_codes(self):
        self.assertEqual(app.classify_video_status(0), "failed")
        self.assertEqual(app.classify_video_status(3), "failed")
        self.assertEqual(app.classify_video_status(1), "processing")
        self.assertEqual(app.classify_video_status(2), "completed")


if __name__ == "__main__":
    unittest.main()
