from datetime import datetime, timedelta

from task_scheduler import TaskScheduler


def fail() -> None:
    raise RuntimeError("Example task failure")


def main() -> None:
    scheduler = TaskScheduler()
    now = datetime.now()

    scheduler.submit(lambda: print("Later task"), now + timedelta(minutes=5))
    scheduler.submit(lambda: print("First due task"), now)
    cancelled_id = scheduler.submit(lambda: print("Should not run"), now)
    scheduler.submit(fail, now)
    scheduler.submit(lambda: print("Still running after failure"), now)
    scheduler.cancel(cancelled_id)

    print("First run:")
    print(f"Attempted: {scheduler.run_due(now)}")
    for result in scheduler.results.values():
        status = "succeeded" if result.succeeded else f"failed: {result.error}"
        print(f"  {result.task_id}: {status}")

    print("\nFive minutes later (simulated, no waiting):")
    print(f"Attempted: {scheduler.run_due(now + timedelta(minutes=5))}")


if __name__ == "__main__":
    main()
