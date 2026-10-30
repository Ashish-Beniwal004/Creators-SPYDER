"""Groq GPT-OSS Chat Completions adapter. Construction never calls an API."""

from copy import deepcopy
import json
import math
from pathlib import Path
from urllib import error, request

from .contracts import ToolCall
from .model import ModelReply, ModelRequest, ProviderError
from .prompts import COMMON_INSTRUCTIONS, STAGE_INSTRUCTIONS, DECISION_SCHEMA, VERIFIER_TOOL
from .quota import TokenLedger

ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
RATE_HEADERS = ("retry-after", "x-ratelimit-limit-requests", "x-ratelimit-limit-tokens",
                "x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens",
                "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens")


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _post_json(payload, api_key, timeout):
    req = request.Request(ENDPOINT, data=json.dumps(payload, allow_nan=False).encode("utf-8"),
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + api_key,
                                   "User-Agent": "SPYDER-Research/0.1"}, method="POST")
    try:
        with request.build_opener(_NoRedirect()).open(req, timeout=timeout) as response:
            value = json.load(response)
            headers = {name: response.headers[name] for name in RATE_HEADERS if response.headers.get(name) is not None}
    except error.HTTPError as exc:
        # Keep status and bounded, redacted server diagnostics; never log auth headers.
        try:
            body = json.loads(exc.read(8192)).get("error", {})
            detail = str(body.get("message", "")).replace(api_key, "[REDACTED]")[:400]
        except (ValueError, AttributeError, OSError):
            detail = ""
        retry = str(exc.headers.get("retry-after", "")).replace(api_key, "[REDACTED]")[:40] if exc.headers else ""
        raise ProviderError(f"Groq HTTP {exc.code}; {detail}; Retry-After={retry or 'unspecified'}; no automatic retry") from None
    except (error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f"Groq transport failure ({type(exc).__name__}); no automatic retry") from None
    except (ValueError, UnicodeError):
        raise ProviderError("Groq returned invalid JSON") from None
    if not isinstance(value, dict):
        raise ProviderError("Groq returned a non-object response")
    value["_rate_limits"] = headers
    return value


class GroqModel:
    def __init__(self, api_key, *, model="openai/gpt-oss-120b", thinking="medium", max_output_tokens=4096,
                 timeout=300, request_interval=90, ledger_path=None, max_total_tokens=170000,
                 transport=None, clock=None, sleep=None):
        if not isinstance(api_key, str) or not api_key.strip() or "\n" in api_key.strip():
            raise ValueError("Set GROQ_API_KEY or provide a nonempty local .groq_api_key file")
        if model != "openai/gpt-oss-120b":
            raise ValueError("This checkpoint adapter is validated for openai/gpt-oss-120b only")
        if thinking not in ("low", "medium", "high"):
            raise ValueError("Thinking must be low, medium or high")
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Invalid timeout")
        self._api_key = api_key.strip()
        self.model, self.thinking = model, thinking
        self.max_output_tokens, self.timeout = max_output_tokens, timeout
        path = ledger_path or Path(__file__).resolve().parents[1] / "experiment_runs/groq_quota_ledger.jsonl"
        helpers = {k: v for k, v in (("clock", clock), ("sleep", sleep)) if v is not None}
        self.ledger = TokenLedger(path, run_limit=max_total_tokens, interval=request_interval, **helpers)
        self._transport = transport or _post_json

    @property
    def metadata(self):
        return {"provider": "groq", "model": self.model, "api": "chat/completions",
                "thinking_level": self.thinking, "max_output_tokens": self.max_output_tokens,
                "timeout_seconds": self.timeout, "request_interval_seconds": self.ledger.interval,
                "automatic_retries": 0, "adapter_version": "0.1.0", "stream": False,
                "reasoning_text_returned": False,
                "token_budget": {"run_limit": self.ledger.run_limit, "rolling_24h_workspace_limit": self.ledger.window_limit,
                                 "per_request_reservation": self.ledger.RESERVATION, "ledger_path": str(self.ledger.path.resolve()),
                                 "input_estimator": "UTF8 JSON bytes / 2, rounded up, plus 256; not exact tokenization",
                                 "scope": "local workspace only; external organization usage must be checked separately"}}

    def build_payload(self, item: ModelRequest):
        body = {"model": self.model, "reasoning_effort": self.thinking, "include_reasoning": False,
                "max_completion_tokens": self.max_output_tokens, "stream": False}
        if item.stage == "final":
            if item.previous_reply is None or len(item.previous_reply.tool_calls) != 1 or item.verification is None:
                raise ValueError("Final stage requires exactly one original tool call and its verifier result")
            raw = item.previous_reply.raw
            body["messages"] = deepcopy(raw["_request_messages"]) + [deepcopy(raw["_assistant_message"]),
                {"role": "tool", "tool_call_id": item.previous_reply.tool_calls[0].call_id,
                 "name": "verify_hypothesis", "content": json.dumps(item.verification, allow_nan=False)},
                {"role": "user", "content": STAGE_INSTRUCTIONS["final"]}]
        elif item.stage in ("baseline", "verify"):
            body["messages"] = [{"role": "system", "content": COMMON_INSTRUCTIONS},
                                {"role": "user", "content": STAGE_INSTRUCTIONS[item.stage] + "\n\n" + json.dumps(item.case.public_payload(), allow_nan=False)}]
        else:
            raise ValueError("Unknown model stage")
        if item.stage == "verify":
            body["tools"] = [{"type": "function", "function": {k: deepcopy(VERIFIER_TOOL[k]) for k in ("name", "description", "parameters")}}]
            body["tool_choice"] = {"type": "function", "function": {"name": "verify_hypothesis"}}
            body["parallel_tool_calls"] = False
        else:
            # Groq does not support tools and structured outputs together. The
            # completed tool history is retained, but no tools are declared here.
            body["response_format"] = {"type": "json_schema", "json_schema": {
                "name": "evidence_decision", "strict": True, "schema": deepcopy(DECISION_SCHEMA)}}
        return body

    def estimate_input_tokens(self, payload):
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return math.ceil(len(encoded) / 2) + 256

    def respond(self, item, emit):
        payload = self.build_payload(item)
        estimate = self.estimate_input_tokens(payload)
        with self.ledger.request(estimate, self.max_output_tokens, emit) as settle:
            emit("provider_request", {"provider": "groq", "body": payload})
            response = self._transport(payload, self._api_key, self.timeout)
            if not isinstance(response, dict):
                raise ProviderError("Groq returned a non-object response")
            response = json.loads(json.dumps(response, allow_nan=False).replace(self._api_key, "[REDACTED]"))
            emit("provider_response", {"provider": "groq", "raw": response})
            usage = response.get("usage", {})
            if not isinstance(usage, dict):
                raise ProviderError("Groq usage is missing; retain reservation and stop")
            values = [usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")]
            if any(type(n) is not int or n < 0 for n in values) or values[0] + values[1] != values[2]:
                raise ProviderError("Groq usage is missing or inconsistent; retain reservation and stop")
            settle(values[2])
            choices = response.get("choices")
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise ProviderError("Groq returned invalid completion choices")
            choice = choices[0]
            message = choice.get("message")
            if not isinstance(message, dict) or message.get("role") != "assistant" or message.get("refusal"):
                raise ProviderError("Groq returned an invalid/refused assistant response")
            expected_finish = "tool_calls" if item.stage == "verify" else "stop"
            if choice.get("finish_reason") != expected_finish:
                raise ProviderError(f"Groq completion did not finish normally: {choice.get('finish_reason')}")
            calls = []
            tool_calls = message.get("tool_calls") or []
            if not isinstance(tool_calls, list):
                raise ProviderError("Groq returned invalid tool calls")
            for call in tool_calls:
                try:
                    if call.get("type") != "function":
                        raise ValueError("Non-function tool")
                    fn = call["function"]
                    arguments = json.loads(fn["arguments"])
                    calls.append(ToolCall(fn["name"], arguments, call["id"]))
                except (ValueError, TypeError, KeyError, AttributeError):
                    raise ProviderError("Groq returned malformed function-call arguments") from None
            if item.stage == "verify" and len(calls) != 1:
                raise ProviderError("Groq verification stage must return exactly one tool call")
            if item.stage != "verify" and calls:
                raise ProviderError("Groq attempted a tool call during a final-decision stage")
            text = message.get("content")
            if text is not None and not isinstance(text, str):
                raise ProviderError("Groq returned invalid assistant content")
            response["_request_messages"] = deepcopy(payload["messages"])
            response["_assistant_message"] = {k: deepcopy(message[k]) for k in ("role", "content", "tool_calls") if k in message}
            return ModelReply(text or "", tuple(calls), response)
