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

    @abstractmethod
    def run(self, data: InputT, tools: "ScopedToolProxy") -> OutputT:
        """Execute the stage. `tools` only exposes bindings named in `allowed_tools`."""
        raise NotImplementedError
