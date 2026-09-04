from __future__ import annotations

import functools

import httpx
import ollama

from app.core.config import Settings
from app.orchestrator.tool_scope import ToolRegistry
from app.orchestrator.tools.hubspot_tools import search_contact, write_contact
from app.orchestrator.tools.ollama_tools import classify_intent


def register_default_tools(registry: ToolRegistry, settings: Settings) -> None:
    """Construct and register every real external-system tool binding this project has.
    `build_production_graph()` calls this once, before compiling the graph, so stages
    reach real tool implementations through `ToolRegistry` rather than an always-empty one."""
    ollama_client = ollama.Client(host=settings.ollama_base_url)
    registry.register("ollama_classify", functools.partial(classify_intent, ollama_client, settings.ollama_model))

    http_client = httpx.Client(timeout=5.0)
    registry.register(
        "hubspot_search_contact",
        functools.partial(search_contact, http_client, settings.hubspot_base_url, settings.hubspot_access_token),
    )
    registry.register(
        "hubspot_write",
        functools.partial(write_contact, http_client, settings.hubspot_base_url, settings.hubspot_access_token),
    )
