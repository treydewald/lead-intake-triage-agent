from __future__ import annotations

from typing import Protocol


class _HttpClient(Protocol):
    def post(self, url: str, *, json: dict, headers: dict[str, str]) -> "_HttpResponse":
        ...


class _HttpResponse(Protocol):
    def raise_for_status(self) -> None:
        ...

    def json(self) -> dict:
        ...


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
