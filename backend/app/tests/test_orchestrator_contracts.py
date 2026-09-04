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


def test_effective_input_slice_falls_back_to_state_slice_when_unset():
    stage = _ConformingStage()
    assert stage.input_slice is None
    assert stage.effective_input_slice == "intake"


def test_effective_input_slice_uses_explicit_input_slice_when_set():
    class _CrossSliceStage(Stage):
        name = "cross_slice"
        input_schema = _Payload
        output_schema = _Payload
        state_slice = "classification"
        input_slice = "intake"

        def run(self, data: _Payload, tools: object) -> _Payload:
            return data

    stage = _CrossSliceStage()
    assert stage.effective_input_slice == "intake"
