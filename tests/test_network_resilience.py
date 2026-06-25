"""Tests for src/nhid_network_resilience.py's retry_with_backoff decorator."""
import os
import sys

import httpx
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.nhid_network_resilience import retry_with_backoff


def _fake_request():
    return httpx.Request("POST", "https://example.test/")


def _status_error(status_code):
    request = _fake_request()
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("boom", request=request, response=response)


class TestSuccessAfterRetries:
    def test_succeeds_after_n_transient_failures(self):
        calls = {"count": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0, jitter=0)
        def flaky():
            calls["count"] += 1
            if calls["count"] < 3:
                raise httpx.ConnectError("connection refused")
            return "ok"

        assert flaky() == "ok"
        assert calls["count"] == 3

    def test_succeeds_after_transient_5xx(self):
        calls = {"count": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0, jitter=0)
        def flaky():
            calls["count"] += 1
            if calls["count"] < 2:
                raise _status_error(503)
            return "ok"

        assert flaky() == "ok"
        assert calls["count"] == 2

    def test_succeeds_after_429(self):
        calls = {"count": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0, jitter=0)
        def flaky():
            calls["count"] += 1
            if calls["count"] < 2:
                raise _status_error(429)
            return "ok"

        assert flaky() == "ok"
        assert calls["count"] == 2


class TestExhaustedRetriesRaise:
    def test_persistent_timeout_raises_after_max_attempts(self):
        calls = {"count": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0, jitter=0)
        def always_fails():
            calls["count"] += 1
            raise httpx.TimeoutException("timed out")

        with pytest.raises(httpx.TimeoutException):
            always_fails()
        assert calls["count"] == 3

    def test_persistent_5xx_raises_after_max_attempts(self):
        calls = {"count": 0}

        @retry_with_backoff(max_attempts=2, base_delay=0, jitter=0)
        def always_fails():
            calls["count"] += 1
            raise _status_error(500)

        with pytest.raises(httpx.HTTPStatusError):
            always_fails()
        assert calls["count"] == 2


class TestNonTransientErrorsDontRetry:
    def test_4xx_other_than_429_raises_immediately(self):
        calls = {"count": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0, jitter=0)
        def bad_request():
            calls["count"] += 1
            raise _status_error(400)

        with pytest.raises(httpx.HTTPStatusError):
            bad_request()
        assert calls["count"] == 1

    def test_programming_error_raises_immediately(self):
        calls = {"count": 0}

        @retry_with_backoff(max_attempts=3, base_delay=0, jitter=0)
        def buggy():
            calls["count"] += 1
            raise ValueError("not a network error")

        with pytest.raises(ValueError):
            buggy()
        assert calls["count"] == 1
