from __future__ import annotations

import hashlib
import pytest

from seasonal.ab import bucket_user


class DummyRequest:
    def __init__(self, cookies=None, meta=None):
        self.COOKIES = cookies or {}
        self.META = meta or {}


def test_bucket_user_with_sid_cookie_stable():
    request = DummyRequest(cookies={"sid": "abc123"})
    other = DummyRequest(cookies={"sid": "abc123"})

    first = bucket_user(request)
    second = bucket_user(other)

    assert 0 <= first < 100
    assert first == second


def test_bucket_user_falls_back_to_user_agent_and_ip():
    request = DummyRequest(meta={"HTTP_USER_AGENT": "TestAgent", "REMOTE_ADDR": "10.0.0.1"})
    other = DummyRequest(meta={"HTTP_USER_AGENT": "TestAgent", "REMOTE_ADDR": "10.0.0.1"})

    first = bucket_user(request)
    second = bucket_user(other)

    assert first == second
    assert 0 <= second < 100


def test_bucket_user_salt_changes_bucket():
    request = DummyRequest(cookies={"sid": "abc123"})
    expected = int(hashlib.sha1("campaign-a:sid:abc123".encode("utf-8")).hexdigest()[:8], 16) % 100
    assert bucket_user(request, salt="campaign-a") == expected
