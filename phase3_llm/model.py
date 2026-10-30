"""Provider-independent requests and a scripted, explicitly non-scientific mock."""

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .contracts import CaseInput, ToolCall
from .prompts import COMMON_INSTRUCTIONS, STAGE_INSTRUCTIONS

EventSink = Callable[[str, dict], None]


class ProviderError(RuntimeError):
    """Provider or quota failure: stop the run without fabricating a decision."""
    pass


@dataclass(frozen=True)
class ModelReply:
    text: str = ""
    tool_calls: tuple[ToolCall, ...] = ()
    raw: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ModelRequest:
    case: CaseInput
    stage: str
    previous_reply: ModelReply | None = None
    verification: dict | None = None

    def public_payload(self) -> dict:
        return {
            "system_instruction": COMMON_INSTRUCTIONS,
            "stage_instruction": STAGE_INSTRUCTIONS[self.stage],
            **self.case.public_payload(),
            **({"verification": self.verification} if self.verification is not None else {}),
        }


class Model(Protocol):
    @property
    def metadata(self) -> dict: ...

    def respond(self, request: ModelRequest, emit: EventSink) -> ModelReply: ...


class ScriptedModel:
    """Replay fixture responses. This is not inference and must not be scored as an LLM."""

    def __init__(self, replies: dict[tuple[tuple[str, str], str], Any]):
        self._replies = replies

    @property
    def metadata(self) -> dict:
        return {"provider": "mock", "model": "scripted-fixtures-v1", "scientific_results": False}

    def respond(self, request: ModelRequest, emit: EventSink) -> ModelReply:
        value = self._replies[(request.case.pair.ids, request.stage)]
        if isinstance(value, BaseException):
            raise value
        if callable(value):
            value = value(request)
        if not isinstance(value, ModelReply):
            raise TypeError("Scripted response must be a ModelReply")
        emit("provider_response", {"provider": "mock", "raw": value.raw})
        return value
