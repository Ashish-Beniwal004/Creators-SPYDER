"""Gemini Interactions REST adapter; constructing it never makes a network request.

Uses the documented stateless history flow, preserving every returned step (including
opaque reasoning signatures) across the single tool round-trip. No built-in tools.
"""

import json
import math
import time
from urllib import error, request

from .contracts import ToolCall
from .model import EventSink, ModelReply, ModelRequest, ProviderError
from .prompts import COMMON_INSTRUCTIONS, DECISION_SCHEMA, STAGE_INSTRUCTIONS, VERIFIER_TOOL

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward an API credential to a redirected endpoint.
        return None


def _post_json(payload: dict, api_key: str, timeout: float) -> dict:
    req = request.Request(ENDPOINT, data=json.dumps(payload, allow_nan=False).encode("utf-8"),
                          headers={"Content-Type": "application/json", "x-goog-api-key": api_key}, method="POST")
    try:
        with request.build_opener(_NoRedirect()).open(req, timeout=timeout) as response:
            value = json.load(response)
    except error.HTTPError as exc:
        # Do not log authentication headers, raw exception URLs, or server-echoed keys.
        raise ProviderError(f"Gemini HTTP {exc.code}; no automatic retry was made") from None
    except (error.URLError, TimeoutError, OSError) as exc:
        raise ProviderError(f"Gemini transport failure ({type(exc).__name__}); no automatic retry was made") from None
    except (ValueError, UnicodeError):
        raise ProviderError("Gemini returned invalid JSON") from None
    if not isinstance(value, dict):
        raise ProviderError("Gemini returned a non-object response")
    return value


class GeminiModel:
    def __init__(self, api_key: str, *, model: str = "gemini-3.8-flash", thinking: str = "medium",
                 max_output_tokens: int = 4096, timeout: float = 300, request_interval: float = 35,
                 transport=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Set GEMINI_API_KEY locally before using Gemini")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Model ID cannot be empty")
        if thinking not in ("low", "medium", "high"):
            raise ValueError("Thinking must be low, medium or high")
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be a positive integer")
        if not math.isfinite(timeout) or timeout <= 0 or not math.isfinite(request_interval) or request_interval < 0:
            raise ValueError("Invalid timeout or request interval")
        self._api_key = api_key
        self.model = model
        self.thinking = thinking
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout
        self.request_interval = request_interval
        self._transport = transport or _post_json
        self._last_request = None

    @property
    def metadata(self) -> dict:
        return {"provider": "gemini", "model": self.model, "api": "interactions/v1beta",
                "thinking_level": self.thinking, "max_output_tokens": self.max_output_tokens,
                "timeout_seconds": self.timeout, "request_interval_seconds": self.request_interval,
                "automatic_retries": 0, "store": False, "adapter_version": "0.1.0"}

    def build_payload(self, item: ModelRequest) -> dict:
        body = {"model": self.model, "store": False,
                "system_instruction": COMMON_INSTRUCTIONS,
                "generation_config": {"thinking_level": self.thinking, "max_output_tokens": self.max_output_tokens}}
        if item.stage == "final":
            if item.previous_reply is None or len(item.previous_reply.tool_calls) != 1 or item.verification is None:
                raise ValueError("Final stage requires the original tool response and verification result")
            previous = item.previous_reply.raw
            body["input"] = previous["_request_input"] + previous["steps"] + [{
                "type": "function_result", "name": "verify_hypothesis",
                "call_id": item.previous_reply.tool_calls[0].call_id,
                "result": [{"type": "text", "text": json.dumps(item.verification, allow_nan=False)}],
            }, {"type": "user_input", "content": [{"type": "text", "text": STAGE_INSTRUCTIONS["final"]}]}]
        else:
            prompt = STAGE_INSTRUCTIONS[item.stage] + "\n\n" + json.dumps(item.case.public_payload(), allow_nan=False)
            body["input"] = [{"type": "user_input", "content": [{"type": "text", "text": prompt}]}]
        if item.stage == "verify":
            body["tools"] = [VERIFIER_TOOL]
            body["generation_config"]["tool_choice"] = "any"
        else:
            body["response_format"] = {"type": "text", "mime_type": "application/json", "schema": DECISION_SCHEMA}
            if item.stage == "final":
                # Retain the declaration for the stateless tool history, but disable new calls.
                body["tools"] = [VERIFIER_TOOL]
                body["generation_config"]["tool_choice"] = "none"
        return body

    def respond(self, item: ModelRequest, emit: EventSink) -> ModelReply:
        payload = self.build_payload(item)
        if self._last_request is not None:
            time.sleep(max(0, self.request_interval - (time.monotonic() - self._last_request)))
        emit("provider_request", {"provider": "gemini", "body": payload})
        self._last_request = time.monotonic()
        raw = self._transport(payload, self._api_key, self.timeout)
        # Accommodate the REST interaction envelope as well as the direct object.
        response = raw.get("interaction", raw)
        if not isinstance(response, dict):
            raise ProviderError("Gemini returned an invalid interaction")
        # Scrub the key even if a server/model unexpectedly echoes it in a payload.
        response = json.loads(json.dumps(response).replace(self._api_key, "[REDACTED]"))
        emit("provider_response", {"provider": "gemini", "raw": response})
        if response.get("status") not in ("completed", "requires_action"):
            raise ProviderError(f"Gemini interaction did not complete: {response.get('status')}")
        steps = response.get("steps", [])
        if not isinstance(steps, list) or any(not isinstance(step, dict) for step in steps):
            raise ProviderError("Gemini returned invalid interaction steps")
        calls, texts = [], []
        for step in steps:
            if step.get("type") == "function_call":
                calls.append(ToolCall(step.get("name"), step.get("arguments"), step.get("id")))
            elif step.get("type") == "text":
                texts.append(step.get("text", ""))
            elif step.get("type") == "model_output":
                content = step.get("content", [])
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    texts.extend(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
        if any(not isinstance(t, str) for t in texts):
            raise ProviderError("Gemini returned invalid text content")
        response["_request_input"] = payload["input"]
        return ModelReply("".join(texts) or response.get("output_text", ""), tuple(calls), response)
