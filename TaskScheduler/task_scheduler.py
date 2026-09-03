"""An in-memory, single-threaded scheduler using local, naive datetimes."""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable
from uuid import uuid4


@dataclass
class Task:
    task_id: str
    scheduled_at: datetime
    submission_index: int
    callback: Callable[[], None]


@dataclass
class TaskResult:
    task_id: str
    succeeded: bool
    error: Exception | None = None


class TaskScheduler:
    def __init__(self) -> None:
        self.scheduled_tasks: dict[datetime, dict[int, Task]] = {}
        self.tasks_by_id: dict[str, Task] = {}
        self.results: dict[str, TaskResult] = {}
        self._next_submission_index = 0

    def submit(
        self, callback: Callable[[], None], scheduled_at: datetime
    ) -> str:
        """Schedule a function once and return its unique ID."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        self._validate_time(scheduled_at)

        task = Task(
            task_id=str(uuid4()),
            scheduled_at=scheduled_at,
            submission_index=self._next_submission_index,
            callback=callback,
        )
        self._next_submission_index += 1
        bucket = self.scheduled_tasks.setdefault(scheduled_at, {})
        bucket[task.submission_index] = task
        self.tasks_by_id[task.task_id] = task
        return task.task_id

    def cancel(self, task_id: str) -> bool:
        """Remove a pending task. Return False if it is no longer pending."""
        task = self.tasks_by_id.pop(task_id, None)
        if task is None:
            return False

        bucket = self.scheduled_tasks[task.scheduled_at]
        del bucket[task.submission_index]
        if not bucket:
            del self.scheduled_tasks[task.scheduled_at]
        return True

    def run_due(self, now: datetime | None = None) -> int:
        """Run tasks due at the start of this call; return attempts, including failures.

        An optional explicit time makes examples and tests deterministic.
        Tasks submitted by callbacks are considered on the next call.
        """
        if now is None:
            now = datetime.now()
        self._validate_time(now)

        due_times = sorted(time for time in self.scheduled_tasks if time <= now)
        # Snapshot before callbacks can submit or cancel tasks.
        due_tasks = [
            task
            for time in due_times
            for task in self.scheduled_tasks[time].values()
        ]

        attempted = 0
        for task in due_tasks:
            # Remove from both indexes before executing. A prior callback may
            # already have cancelled this task, in which case we skip it.
            if not self.cancel(task.task_id):
                continue

            attempted += 1
            try:
                task.callback()
            except Exception as error:
                self.results[task.task_id] = TaskResult(task.task_id, False, error)
            else:
                self.results[task.task_id] = TaskResult(task.task_id, True)

        return attempted

    @staticmethod
    def _validate_time(value: datetime) -> None:
        if value.tzinfo is not None and value.utcoffset() is not None:
            raise ValueError("Use a naive local datetime, such as datetime.now()")
