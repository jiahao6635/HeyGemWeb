import os
import shutil
import tempfile
import threading
import unittest


TEST_DATA_ROOT = tempfile.mkdtemp(prefix="heygemweb-task-tests-")
os.environ["HEYGEM_BASE_DIR"] = TEST_DATA_ROOT

from services.task_service import Task, TaskPriority, TaskQueue, TaskStatus, TaskType  # noqa: E402


class TaskModelTest(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_DATA_ROOT, ignore_errors=True)

    def test_higher_priority_tasks_sort_first(self):
        normal = Task("normal", TaskType.FILE_CLEANUP, {}, "alice", TaskPriority.NORMAL)
        urgent = Task("urgent", TaskType.VIDEO_GENERATION, {}, "alice", TaskPriority.URGENT)

        self.assertEqual(sorted([normal, urgent])[0], urgent)

    def test_serializes_initial_task_state(self):
        task = Task("task-1", TaskType.AUDIO_SYNTHESIS, {"text": "hello"}, "alice")
        result = task.to_dict()

        self.assertEqual(result["task_id"], "task-1")
        self.assertEqual(result["task_type"], TaskType.AUDIO_SYNTHESIS)
        self.assertEqual(result["status"], TaskStatus.PENDING)
        self.assertEqual(result["username"], "alice")
        self.assertEqual(result["progress"], 0)

    def test_terminal_callback_failure_does_not_deadlock_queue(self):
        callback_started = threading.Event()

        def fail(_task):
            callback_started.set()
            raise RuntimeError("expected failure")

        task_queue = TaskQueue(max_concurrent_tasks=1)
        task = Task("failing-task", TaskType.FILE_CLEANUP, {}, "alice", callback=fail)
        task.max_retries = 0

        task_queue.running = True
        task_queue.worker_thread.start()
        try:
            task_queue.add_task(task)
            self.assertTrue(callback_started.wait(timeout=3))
            task_queue.running = False
            task_queue.worker_thread.join(timeout=3)
            self.assertFalse(task_queue.worker_thread.is_alive())

            with task_queue.lock:
                completed = task_queue.completed_tasks.get(task.task_id)
                self.assertIsNotNone(completed)
                self.assertEqual(completed.status, TaskStatus.FAILED)
                self.assertNotIn(task.task_id, task_queue.active_tasks)
        finally:
            task_queue.running = False
            task_queue.worker_thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
