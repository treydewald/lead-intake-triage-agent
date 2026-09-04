from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.orchestrator.tool_scope import ScopedToolProxy

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class Stage(ABC, Generic[InputT, OutputT]):
    """Contract every pipeline stage implements.

    A stage declares its input/output schema, the exact tool names it may call, and
    the single `LeadPipelineState` slice it reads/writes. `tool_scope.py` enforces the
    `allowed_tools` declaration at runtime rather than trusting stage code to self-police
    it — this is what makes the per-stage tool/state boundary real under code inspection.
    """

    name: ClassVar[str]
    input_schema: ClassVar[type[BaseModel]]
    output_schema: ClassVar[type[BaseModel]]
    allowed_tools: ClassVar[frozenset[str]] = frozenset()
    state_slice: ClassVar[str]
    input_slice: ClassVar[str | None] = None

    @property
    def effective_input_slice(self) -> str:
        """The `LeadPipelineState` slice this stage actually reads. Defaults to
        `state_slice` (a stage that transforms its own slice in place); a stage that
        reads a different slice than it writes (e.g. one reading `intake` but writing
        `classification`) overrides `input_slice` instead."""
        return self.input_slice or self.state_slice

    @abstractmethod
    def run(self, data: InputT, tools: "ScopedToolProxy") -> OutputT:
        """Execute the stage. `tools` only exposes bindings named in `allowed_tools`."""
        raise NotImplementedError
