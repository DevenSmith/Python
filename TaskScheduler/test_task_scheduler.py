import unittest
from datetime import datetime, timedelta

from task_scheduler import TaskScheduler


class TaskSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = TaskScheduler()
        self.now = datetime(2026, 9, 3, 10)

    def test_time_order_ties_and_future_tasks(self) -> None:
        seen = []
        future = self.now + timedelta(minutes=5)
        self.scheduler.submit(lambda: seen.append("future"), future)
        self.scheduler.submit(lambda: seen.append("first"), self.now)
        self.scheduler.submit(lambda: seen.append("second"), self.now)
        self.scheduler.submit(
            lambda: seen.append("past"), self.now - timedelta(minutes=1)
        )
        self.assertEqual(self.scheduler.run_due(self.now), 3)
        self.assertEqual(seen, ["past", "first", "second"])
        self.assertEqual(self.scheduler.run_due(future), 1)
        self.assertEqual(seen[-1], "future")
        self.assertEqual(self.scheduler.run_due(future), 0)

    def test_cancellation_and_empty_bucket_cleanup(self) -> None:
        task_id = self.scheduler.submit(lambda: self.fail("Cancelled task ran"), self.now)
        self.assertTrue(self.scheduler.cancel(task_id))
        self.assertFalse(self.scheduler.cancel(task_id))
        self.assertFalse(self.scheduler.cancel("unknown"))
        self.assertEqual(self.scheduler.run_due(self.now), 0)
        self.assertEqual(self.scheduler.scheduled_tasks, {})
        self.assertEqual(self.scheduler.tasks_by_id, {})

    def test_failure_is_recorded_without_retry_or_stopping_other_tasks(self) -> None:
        seen = []

        def fail() -> None:
            raise ValueError("Expected failure")

        failed_id = self.scheduler.submit(fail, self.now)
        success_id = self.scheduler.submit(lambda: seen.append("success"), self.now)
        self.assertEqual(self.scheduler.run_due(self.now), 2)
        self.assertEqual(seen, ["success"])
        self.assertFalse(self.scheduler.results[failed_id].succeeded)
        self.assertIsInstance(self.scheduler.results[failed_id].error, ValueError)
        self.assertTrue(self.scheduler.results[success_id].succeeded)
        self.assertEqual(self.scheduler.run_due(self.now), 0)
        self.assertEqual(self.scheduler.scheduled_tasks, {})
        self.assertEqual(self.scheduler.tasks_by_id, {})

    def test_callbacks_can_cancel_and_submit(self) -> None:
        seen = []

        def first() -> None:
            self.scheduler.cancel(cancelled_id)
            self.scheduler.submit(lambda: seen.append("new"), self.now)

        self.scheduler.submit(first, self.now)
        cancelled_id = self.scheduler.submit(lambda: seen.append("cancelled"), self.now)
        self.assertEqual(self.scheduler.run_due(self.now), 1)
        self.assertEqual(seen, [])
        self.assertEqual(self.scheduler.run_due(self.now), 1)
        self.assertEqual(seen, ["new"])


if __name__ == "__main__":
    unittest.main()
