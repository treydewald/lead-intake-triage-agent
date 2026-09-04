import pytest
from pydantic import BaseModel

from app.orchestrator.contracts import Stage


class _Payload(BaseModel):
    value: int = 0


class _ConformingStage(Stage):
    name = "conforming"
    input_schema = _Payload
    output_schema = _Payload
    allowed_tools = frozenset({"some_tool"})
    state_slice = "intake"

    def run(self, data: _Payload, tools: object) -> _Payload:
        return _Payload(value=data.value + 1)


def test_conforming_stage_can_be_instantiated_and_run():
    stage = _ConformingStage()
    result = stage.run(_Payload(value=1), tools=None)
    assert result.value == 2


def test_non_conforming_stage_is_rejected():
    class _MissingRun(Stage):
        name = "broken"
        input_schema = _Payload
        output_schema = _Payload
        state_slice = "intake"

    with pytest.raises(TypeError):
        _MissingRun()  # abstract method `run` not implemented
