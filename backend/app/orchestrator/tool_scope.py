from __future__ import annotations

from typing import Callable

from app.orchestrator.errors import OutOfScopeToolError

ToolFunc = Callable[..., object]


class ToolRegistry:
    """Central registry of every tool binding in the system, keyed by tool name.

    Stage code never touches this directly. The orchestrator hands each stage a
    `ScopedToolProxy` (via `scoped_proxy`) restricted to that stage's declared
    `allowed_tools` — this is the only path any stage may use to reach a tool binding.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolFunc] = {}

    def register(self, name: str, func: ToolFunc) -> None:
        self._tools[name] = func

    def scoped_proxy(self, allowed_tools: frozenset[str], stage_name: str) -> "ScopedToolProxy":
        return ScopedToolProxy(self._tools, allowed_tools, stage_name)


class ScopedToolProxy:
    """A view over the registry restricted to one stage's declared tool set.

    Calling any tool name outside `allowed_tools` raises `OutOfScopeToolError` — caught
    and logged by the orchestrator, never a silent no-op. This is the direct enforcement
    point for the project's per-stage tool-access boundary (its stated Critical risk).
    """

    def __init__(self, tools: dict[str, ToolFunc], allowed_tools: frozenset[str], stage_name: str) -> None:
        self._tools = tools
        self._allowed_tools = allowed_tools
        self._stage_name = stage_name

    def call(self, tool_name: str, *args: object, **kwargs: object) -> object:
        if tool_name not in self._allowed_tools:
            raise OutOfScopeToolError(
                f"Stage '{self._stage_name}' attempted out-of-scope tool call: '{tool_name}'"
            )
        if tool_name not in self._tools:
            raise KeyError(f"Tool '{tool_name}' is not registered in the ToolRegistry")
        return self._tools[tool_name](*args, **kwargs)
