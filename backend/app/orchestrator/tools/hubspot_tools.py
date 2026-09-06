from __future__ import annotations

import time
import uuid
from typing import Callable, Protocol

import httpx


class _HttpClient(Protocol):
    def post(self, url: str, *, json: dict, headers: dict[str, str]) -> "_HttpResponse":
        ...

    def patch(self, url: str, *, json: dict, headers: dict[str, str]) -> "_HttpResponse":
        ...


class _HttpResponse(Protocol):
    status_code: int
    headers: dict[str, str]

    def raise_for_status(self) -> None:
        ...

    def json(self) -> dict:
        ...


class HubSpotWriteError(Exception):
    """Raised by `write_contact` on a non-retryable failure or exhausted retries.
    Deliberately never caught by `HubSpotCrmWriteStage.run()` — see
    architecture-plan-feature-05.md's Architecture Rule Change #1 (reworded failure-
    handling Key Decision): this feature's spec wants the pipeline to halt at this stage,
    not continue past a write failure."""


def _require_token(token: str | None) -> str:
    """A blank token (unset `HUBSPOT_ACCESS_TOKEN`) produces an `Authorization: Bearer `
    header value ending in whitespace, which httpx/h11 rejects at send-time as an
    `httpx.LocalProtocolError` ("Illegal header value b'Bearer '") — a raw transport
    exception, not `httpx.HTTPStatusError`, so it isn't caught by either caller's own
    error handling and instead leaks verbatim into the pipeline run's failure message.
    Checked up front so a missing token fails with a message that actually says so."""
    if not token:
        raise HubSpotWriteError(
            "HubSpot access token is not configured (HUBSPOT_ACCESS_TOKEN is empty) — "
            "see backend/.env.example."
        )
    return token


def _build_filter(*, phone: str | None, email: str | None, name: str | None) -> dict:
    if phone is not None:
        return {"propertyName": "phone", "operator": "EQ", "value": phone}
    if email is not None:
        return {"propertyName": "email", "operator": "EQ", "value": email}
    return {"propertyName": "name", "operator": "CONTAINS_TOKEN", "value": name}


def search_contact(
    client: _HttpClient,
    base_url: str,
    token: str | None,
    *,
    phone: str | None = None,
    email: str | None = None,
    name: str | None = None,
) -> dict | None:
    """Issue one read-only HubSpot CRM Search API call and return the first matching
    contact's properties, or `None` if no result exists. Exact-key filter on phone/email
    when given (checked in that order), else a fuzzy `CONTAINS_TOKEN` filter on name. No
    confidence scoring here — that's `DataEnrichmentStage`'s responsibility, keeping this
    binding thin and swappable, matching `classify_intent`'s precedent. Raises on
    HTTP/timeout error; the stage owns all failure handling."""
    token = _require_token(token)
    response = client.post(
        f"{base_url}/crm/v3/objects/contacts/search",
        json={"filterGroups": [{"filters": [_build_filter(phone=phone, email=email, name=name)]}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return None
    return results[0]["properties"]


_RETRYABLE_STATUS_CODES = {429}


def _is_retryable(status_code: int) -> bool:
    return status_code in _RETRYABLE_STATUS_CODES or 500 <= status_code < 600


def write_contact(
    client: _HttpClient,
    base_url: str,
    token: str | None,
    *,
    phone: str | None = None,
    email: str | None = None,
    properties: dict,
    max_retries: int = 3,
    base_delay: float = 0.5,
    sleep: Callable[[float], None] = time.sleep,
) -> dict:
    """Idempotent create-or-update against HubSpot's Contacts API, write-only (no
    `allowed_tools` other than this may reach it — see
    `.claude/portfolio-reference.md`'s Key Decisions).

    Dedupe lookup reuses `search_contact` directly, exact-key only (phone checked first,
    then email) — deliberately no name-fuzzy fallback, since a false-positive match here
    would silently corrupt a real external CRM record rather than just this project's own
    local state. A match found is then addressed by its own dedupe-key *value* via
    HubSpot's `idProperty` upsert query parameter, so no second lookup is needed to
    recover the contact's internal id — `search_contact`'s return shape (properties only,
    no id) stays completely unmodified. Neither phone nor email given -> always create,
    `dedupe_uncertain=True`, per the spec's own edge case.

    Each retry re-runs the *whole* attempt (lookup + write), not just the write — the
    lookup is a read and idempotent by construction, so a stale first-attempt lookup can
    never cause a duplicate create on a later attempt (see architecture-plan-feature-05.md
    Risks). A 429/5xx response retries up to `max_retries` times with backoff (`sleep`
    injected so tests never incur real delay); 401/403 raises immediately, no retry; any
    other 4xx raises immediately, no retry; retries exhausted on a retryable error raises.

    A blank/unset `token` is treated as "no live CRM configured" rather than an error: no
    HTTP call is made (there's nothing to authenticate), and the write is recorded as
    `status="simulated"` so the pipeline completes end-to-end instead of halting — see
    `.claude/portfolio-reference.md`'s Key Decisions. This only applies to the write path;
    `search_contact` (a real external read) still raises on a missing token via
    `_require_token`, since it has no equivalent honest fallback.
    """
    if not token:
        dedupe_key_used = "phone" if phone is not None else ("email" if email is not None else None)
        return {
            "id": f"simulated-{uuid.uuid4()}",
            "status": "simulated",
            "dedupe_key_used": dedupe_key_used,
            "dedupe_uncertain": dedupe_key_used is None,
            "retry_count": 0,
        }

    headers = {"Authorization": f"Bearer {token}"}
    retry_count = 0

    for attempt in range(max_retries + 1):
        dedupe_key_used: str | None = "phone" if phone is not None else ("email" if email is not None else None)
        dedupe_uncertain = dedupe_key_used is None

        try:
            match = None
            if dedupe_key_used is not None:
                match = search_contact(client, base_url, token, phone=phone, email=email)

            if match is not None:
                key_value = phone if dedupe_key_used == "phone" else email
                url = f"{base_url}/crm/v3/objects/contacts/{key_value}?idProperty={dedupe_key_used}"
                response = client.patch(url, json={"properties": properties}, headers=headers)
                status = "updated"
            else:
                url = f"{base_url}/crm/v3/objects/contacts"
                response = client.post(url, json={"properties": properties}, headers=headers)
                status = "created"

            response.raise_for_status()
            return {
                "id": response.json()["id"],
                "status": status,
                "dedupe_key_used": dedupe_key_used,
                "dedupe_uncertain": dedupe_uncertain,
                "retry_count": retry_count,
            }
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            if status_code in (401, 403):
                raise HubSpotWriteError(f"HubSpot auth failed ({status_code}): {exc}") from exc
            if not _is_retryable(status_code):
                raise HubSpotWriteError(f"HubSpot write rejected ({status_code}): {exc}") from exc
            if attempt >= max_retries:
                raise HubSpotWriteError(f"HubSpot write failed after {max_retries} retries: {exc}") from exc
            retry_after = exc.response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after is not None else base_delay * 2**attempt
            sleep(delay)
            retry_count += 1

    raise HubSpotWriteError("HubSpot write failed: retry loop exhausted unexpectedly")
