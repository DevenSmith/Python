from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from threading import Lock
from typing import Callable
from uuid import uuid4


class ConnectionRequestError(Exception):
    """Base error carrying the HTTP status an API adapter should return."""

    status_code = 500


class BackendUnavailable(ConnectionRequestError):
    status_code = 503


class DuplicateRequest(ConnectionRequestError):
    status_code = 409


class RequestedUserBlocked(ConnectionRequestError):
    status_code = 403


class AlreadyFriends(ConnectionRequestError):
    status_code = 409


class InvalidTimestamp(ConnectionRequestError):
    status_code = 422


@dataclass(frozen=True)
class ConnectionRequest:
    request_id: str
    sending_user_id: str
    requested_user_id: str
    sent_time: datetime
    status: str
    last_updated_time: datetime


class InMemoryConnectionRepository:
    """Thread-safe fake repository suitable for unit tests and demos."""

    def __init__(self) -> None:
        self.requests: dict[str, ConnectionRequest] = {}
        self.blocked_pairs: set[frozenset[str]] = set()
        self.friend_pairs: set[frozenset[str]] = set()
        self.available = True
        self._lock = Lock()

    @staticmethod
    def pair(first_user_id: str, second_user_id: str) -> frozenset[str]:
        return frozenset((first_user_id, second_user_id))

    def create(self, request: ConnectionRequest) -> ConnectionRequest:
        with self._lock:
            if not self.available:
                raise BackendUnavailable("Connection backend is unavailable")

            pair = self.pair(request.sending_user_id, request.requested_user_id)
            if pair in self.blocked_pairs:
                raise RequestedUserBlocked("A user in this pair is blocked")
            if pair in self.friend_pairs:
                raise AlreadyFriends("Users are already friends")
            if any(
                self.pair(item.sending_user_id, item.requested_user_id) == pair
                and item.status == "pending"
                for item in self.requests.values()
            ):
                raise DuplicateRequest("A pending request already exists")

            self.requests[request.request_id] = request
            return request


class ConnectionRequestService:
    def __init__(
        self,
        repository: InMemoryConnectionRepository,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.repository = repository
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def create(self, sending_user_id: str, requested_user_id: str) -> ConnectionRequest:
        now = self.clock()
        validate_timestamp(now, datetime.now(timezone.utc))
        request = ConnectionRequest(
            request_id=f"cr_{uuid4().hex}",
            sending_user_id=sending_user_id,
            requested_user_id=requested_user_id,
            sent_time=now,
            status="pending",
            last_updated_time=now,
        )
        return self.repository.create(request)


def validate_timestamp(value: object, now: datetime) -> None:
    if not isinstance(value, datetime):
        raise InvalidTimestamp("Timestamp must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidTimestamp("Timestamp must include a timezone")
    if value > now:
        raise InvalidTimestamp("Timestamp cannot be in the future")


def pending_request(
    sending_user_id: str,
    requested_user_id: str,
    sent_time: datetime,
) -> ConnectionRequest:
    """Convenience factory for repository fixtures."""
    return ConnectionRequest(
        request_id=f"cr_{uuid4().hex}",
        sending_user_id=sending_user_id,
        requested_user_id=requested_user_id,
        sent_time=sent_time,
        status="pending",
        last_updated_time=sent_time,
    )
