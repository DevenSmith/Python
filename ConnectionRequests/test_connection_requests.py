from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import unittest

from connection_requests import (
    AlreadyFriends,
    BackendUnavailable,
    ConnectionRequestService,
    DuplicateRequest,
    InMemoryConnectionRepository,
    InvalidTimestamp,
    RequestedUserBlocked,
    pending_request,
    validate_timestamp,
)


SENDER = "user_1001"
RECIPIENT = "user_2002"
NOW = datetime(2026, 9, 7, 16, 30, tzinfo=timezone.utc)


class CreateConnectionRequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryConnectionRepository()
        self.service = ConnectionRequestService(self.repository, clock=lambda: NOW)

    def test_standard_success(self) -> None:
        result = self.service.create(SENDER, RECIPIENT)

        self.assertTrue(result.request_id.startswith("cr_"))
        self.assertEqual(result.sending_user_id, SENDER)
        self.assertEqual(result.requested_user_id, RECIPIENT)
        self.assertEqual(result.status, "pending")
        self.assertEqual(result.sent_time, NOW)
        self.assertEqual(result.last_updated_time, NOW)
        self.assertEqual(len(self.repository.requests), 1)

    def test_backend_not_available(self) -> None:
        self.repository.available = False

        with self.assertRaisesRegex(BackendUnavailable, "unavailable") as caught:
            self.service.create(SENDER, RECIPIENT)

        self.assertEqual(caught.exception.status_code, 503)
        self.assertEqual(self.repository.requests, {})

    def test_multiple_identical_requests_only_create_one(self) -> None:
        def submit(_: int):
            try:
                return self.service.create(SENDER, RECIPIENT)
            except DuplicateRequest as error:
                return error

        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(submit, range(5)))

        successes = [item for item in results if not isinstance(item, Exception)]
        duplicates = [item for item in results if isinstance(item, DuplicateRequest)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(duplicates), 4)
        self.assertEqual(len(self.repository.requests), 1)

    def test_duplicate_pending_request_already_exists(self) -> None:
        existing = pending_request(SENDER, RECIPIENT, NOW)
        self.repository.requests[existing.request_id] = existing

        with self.assertRaises(DuplicateRequest) as caught:
            self.service.create(SENDER, RECIPIENT)

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(len(self.repository.requests), 1)

    def test_requested_user_is_blocked(self) -> None:
        self.repository.blocked_pairs.add(self.repository.pair(SENDER, RECIPIENT))

        with self.assertRaises(RequestedUserBlocked) as caught:
            self.service.create(SENDER, RECIPIENT)

        self.assertEqual(caught.exception.status_code, 403)
        self.assertEqual(self.repository.requests, {})

    def test_users_are_already_friends(self) -> None:
        self.repository.friend_pairs.add(self.repository.pair(SENDER, RECIPIENT))

        with self.assertRaises(AlreadyFriends) as caught:
            self.service.create(SENDER, RECIPIENT)

        self.assertEqual(caught.exception.status_code, 409)
        self.assertEqual(self.repository.requests, {})

    def test_future_timestamp_is_rejected(self) -> None:
        with self.assertRaises(InvalidTimestamp):
            validate_timestamp(NOW + timedelta(seconds=1), NOW)

    def test_timezone_naive_timestamp_is_rejected(self) -> None:
        with self.assertRaises(InvalidTimestamp):
            validate_timestamp(datetime(2026, 9, 7, 16, 30), NOW)

    def test_non_datetime_timestamp_is_rejected(self) -> None:
        with self.assertRaises(InvalidTimestamp):
            validate_timestamp("not-a-time", NOW)


if __name__ == "__main__":
    unittest.main()
