# Task scheduler interview practice

Requires Python 3.10 or newer; no external packages.

From this folder:

```powershell
python demo.py
python -m unittest -v
```

`task_scheduler.py` implements the proposed two-dictionary design:

- `scheduled_tasks`: scheduled datetime -> submission index -> Task.
- `tasks_by_id`: task ID -> the same Task object, for quick cancellation.
- `results`: task ID -> success or failure record, including the exception.

`submit(callback, scheduled_at)` returns the generated task ID. `cancel(task_id)`
returns whether a pending task was removed. `run_due()` runs tasks in scheduled
time order, breaking ties by submission order, and returns the number attempted.
Pass an optional `now` to simulate time in examples or tests.

Use naive local datetimes consistently (for example `datetime.now()`). This
exercise is in memory and single threaded, without automatic timers, recurrence,
retries, or persistence. The caller invokes `run_due()`. Failed tasks are recorded
and other due tasks continue. Tasks submitted during execution wait until the
next call; pending tasks cancelled by callbacks are skipped. Result history stays
in memory until the caller clears it.

With n pending tasks, b distinct scheduled timestamps, d due timestamps, and k
due tasks, submission and cancellation are average O(1). Finding and executing
due tasks costs O(b + d log d + k), excluding callback execution time.
