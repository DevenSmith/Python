from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock

from fastapi import HTTPException, status

from tinyrpg.config import settings


class LoginRateLimiter:
    """Small in-process limiter suitable for this single-process teaching app."""

    def __init__(self) -> None:
        self.attempts: dict[str, deque[datetime]] = defaultdict(deque)
        self.lock = Lock()

    def check(self, key: str, now: datetime) -> None:
        cutoff = now - timedelta(minutes=settings.login_attempt_window_minutes)
        with self.lock:
            attempts = self.attempts[key]
            while attempts and attempts[0] <= cutoff:
                attempts.popleft()
            if len(attempts) >= settings.login_attempt_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Try again later.",
                    headers={"Retry-After": str(settings.login_attempt_window_minutes * 60)},
                )

    def failed(self, key: str, now: datetime) -> None:
        with self.lock:
            self.attempts[key].append(now)

    def succeeded(self, key: str) -> None:
        with self.lock:
            self.attempts.pop(key, None)

    def clear_email(self, email: str) -> None:
        suffix = f":{email.lower()}"
        with self.lock:
            for key in [key for key in self.attempts if key.endswith(suffix)]:
                del self.attempts[key]

    def clear(self) -> None:
        with self.lock:
            self.attempts.clear()


login_rate_limiter = LoginRateLimiter()
