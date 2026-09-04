from __future__ import annotations

import functools

import ollama

from app.core.config import Settings
from app.orchestrator.tool_scope import ToolRegistry
from app.orchestrator.tools.ollama_tools import classify_intent


def register_default_tools(registry: ToolRegistry, settings: Settings) -> None:
    """Construct and register every real external-system tool binding this project has.
    `build_production_graph()` calls this once, before compiling the graph, so stages
    reach real tool implementations through `ToolRegistry` rather than an always-empty one."""
    client = ollama.Client(host=settings.ollama_base_url)
    registry.register("ollama_classify", functools.partial(classify_intent, client, settings.ollama_model))
