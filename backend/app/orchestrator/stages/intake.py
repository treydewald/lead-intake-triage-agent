from __future__ import annotations

import re
from email import message_from_string
from email.message import Message
from email.utils import parseaddr
from typing import TYPE_CHECKING

from app.orchestrator.contracts import Stage
from app.orchestrator.state import IntakeSlice

if TYPE_CHECKING:
    from app.orchestrator.tool_scope import ScopedToolProxy

_PHONE_DIGITS_RE = re.compile(r"\D+")
_PHONE_CANDIDATE_RE = re.compile(r"(\+?\d[\d\-.\s()]{7,}\d)")


def _normalize_phone(phone: str | None) -> str | None:
    if phone is None:
        return None
    digits = _PHONE_DIGITS_RE.sub("", phone)
    return digits or None


def _normalize_email(email: str | None) -> str | None:
    if email is None:
        return None
    normalized = email.strip().lower()
    return normalized or None


def _is_blank(text: str | None) -> bool:
    return text is None or text.strip() == ""


def _extract_email_body(msg: Message, raw_text: str) -> str | None:
    if msg.is_multipart():
        parts: list[str] = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.is_multipart():
                payload = part.get_payload(decode=True)
                if payload is not None:
                    charset = part.get_content_charset() or "utf-8"
                    parts.append(payload.decode(charset, errors="replace"))
        body = "\n".join(parts).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload is not None:
            charset = msg.get_content_charset() or "utf-8"
            body = payload.decode(charset, errors="replace").strip()
        else:
            text = msg.get_payload()
            body = text.strip() if isinstance(text, str) else ""
    return body or raw_text.strip() or None


class IntakeStage(Stage[IntakeSlice, IntakeSlice]):
    """Feature 02: normalizes a raw inbound lead (web form / email / callback
    transcript) into the structured `IntakeSlice` the rest of the pipeline consumes.

    `input_schema == output_schema == IntakeSlice`, per Feature 01's `default_stages()`
    convention (see `.claude/portfolio-reference.md`'s Key Decisions) — the caller
    building the initial `LeadPipelineState` seeds raw/unprocessed values into these same
    fields, and `run()` overwrites them in place with the normalized version.
    """

    name = "intake_parsing"
    input_schema = IntakeSlice
    output_schema = IntakeSlice
    allowed_tools = frozenset()
    state_slice = "intake"

    def run(self, data: IntakeSlice, tools: "ScopedToolProxy") -> IntakeSlice:
        if data.source_channel == "email":
            working = self._parse_email(data)
        elif data.source_channel == "callback":
            working = self._parse_callback(data)
        else:
            working = data

        name = working.name.strip() or None if working.name else None
        phone = _normalize_phone(working.phone)
        email = _normalize_email(working.email)
        message_body = working.message_body

        return working.model_copy(
            update={
                "name": name,
                "phone": phone,
                "email": email,
                "empty_message": _is_blank(message_body),
                "low_identifiability": name is None and phone is None and email is None,
            }
        )

    def _parse_email(self, data: IntakeSlice) -> IntakeSlice:
        """Extract sender name/email and body from raw email text via the stdlib `email`
        module. Never raises — a message that doesn't parse into a recognizable structure
        (e.g. no headers at all) naturally degrades to no sender fields and the full raw
        text as the body, which is exactly the spec's malformed-email fallback."""
        raw_text = data.message_body or ""
        try:
            msg = message_from_string(raw_text)
            sender_name, sender_email = parseaddr(msg.get("From", ""))
            body = _extract_email_body(msg, raw_text)
            return data.model_copy(
                update={
                    "name": sender_name or None,
                    "email": sender_email or None,
                    "message_body": body,
                }
            )
        except Exception:
            return data.model_copy(
                update={"name": None, "email": None, "phone": None, "message_body": raw_text or None}
            )

    def _parse_callback(self, data: IntakeSlice) -> IntakeSlice:
        """Extract a phone number from the transcript if one is present; the transcript
        itself always remains the message body."""
        transcript = data.message_body or ""
        match = _PHONE_CANDIDATE_RE.search(transcript)
        phone = match.group(1) if match else data.phone
        return data.model_copy(update={"phone": phone, "message_body": transcript or None})
