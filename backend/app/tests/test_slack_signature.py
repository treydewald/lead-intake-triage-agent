from __future__ import annotations

import hashlib
import hmac
import time

from app.routers.slack import verify_slack_signature

SECRET = "test-signing-secret"


def _sign(*, secret: str, timestamp: str, body: bytes) -> str:
    basestring = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), basestring, hashlib.sha256).hexdigest()


def test_valid_signature_and_fresh_timestamp_is_accepted():
    body = b"payload=%7B%22ok%22%3Atrue%7D"
    timestamp = str(int(time.time()))
    signature = _sign(secret=SECRET, timestamp=timestamp, body=body)

    assert verify_slack_signature(signing_secret=SECRET, timestamp=timestamp, body=body, signature=signature) is True


def test_forged_signature_is_rejected():
    body = b"payload=%7B%22ok%22%3Atrue%7D"
    timestamp = str(int(time.time()))
    forged = _sign(secret="wrong-secret", timestamp=timestamp, body=body)

    assert verify_slack_signature(signing_secret=SECRET, timestamp=timestamp, body=body, signature=forged) is False


def test_tampered_body_invalidates_a_previously_valid_signature():
    original_body = b"payload=%7B%22ok%22%3Atrue%7D"
    timestamp = str(int(time.time()))
    signature = _sign(secret=SECRET, timestamp=timestamp, body=original_body)

    tampered_body = b"payload=%7B%22ok%22%3Afalse%7D"

    assert (
        verify_slack_signature(signing_secret=SECRET, timestamp=timestamp, body=tampered_body, signature=signature)
        is False
    )


def test_stale_timestamp_is_rejected_even_with_a_correct_signature():
    body = b"payload=%7B%22ok%22%3Atrue%7D"
    stale_timestamp = str(int(time.time()) - 600)  # 10 minutes old
    signature = _sign(secret=SECRET, timestamp=stale_timestamp, body=body)

    assert (
        verify_slack_signature(signing_secret=SECRET, timestamp=stale_timestamp, body=body, signature=signature)
        is False
    )


def test_unconfigured_secret_always_rejects():
    body = b"payload=%7B%22ok%22%3Atrue%7D"
    timestamp = str(int(time.time()))
    signature = _sign(secret=SECRET, timestamp=timestamp, body=body)

    assert verify_slack_signature(signing_secret=None, timestamp=timestamp, body=body, signature=signature) is False


def test_missing_signature_header_rejects():
    body = b"payload=%7B%22ok%22%3Atrue%7D"
    timestamp = str(int(time.time()))

    assert verify_slack_signature(signing_secret=SECRET, timestamp=timestamp, body=body, signature=None) is False


def test_missing_timestamp_header_rejects():
    body = b"payload=%7B%22ok%22%3Atrue%7D"
    signature = _sign(secret=SECRET, timestamp="1700000000", body=body)

    assert verify_slack_signature(signing_secret=SECRET, timestamp=None, body=body, signature=signature) is False


def test_non_numeric_timestamp_rejects():
    body = b"payload=%7B%22ok%22%3Atrue%7D"
    signature = _sign(secret=SECRET, timestamp="not-a-number", body=body)

    assert (
        verify_slack_signature(signing_secret=SECRET, timestamp="not-a-number", body=body, signature=signature)
        is False
    )
