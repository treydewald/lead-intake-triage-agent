class OutOfScopeToolError(Exception):
    """Raised when a stage attempts to call a tool name outside its contract's allowed_tools."""


class StageExecutionError(Exception):
    """Raised when a stage's run() raises; carries the stage name for trace/halt logic."""

    def __init__(self, stage_name: str, original: Exception) -> None:
        self.stage_name = stage_name
        self.original = original
        super().__init__(f"Stage '{stage_name}' failed: {original}")


class StateValidationError(Exception):
    """Raised when state passed between stages fails schema validation."""
