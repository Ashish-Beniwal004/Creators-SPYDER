"""Conservative local Groq quota accounting, shared across smoke/experiment runs.

This is a rolling 24-hour workspace ledger, not authoritative organization usage.
Unknown usage retains a full 8,000-token reservation. No automatic retry/reset.
"""

from contextlib import contextmanager
import json
import math
from pathlib import Path
import time
from uuid import uuid4

from .model import ProviderError


class TokenLedger:
    RESERVATION = 8000

    def __init__(self, path, *, run_limit=170000, window_limit=180000, interval=90,
                 clock=time.time, sleep=time.sleep):
        if type(run_limit) is not int or type(window_limit) is not int or not 8000 <= run_limit <= window_limit <= 180000:
            raise ValueError("Groq token budgets require 8000 <= run limit <= window limit <= 180000")
        if not math.isfinite(interval) or interval < 0:
            raise ValueError("Invalid request interval")
        self.path = Path(path)
        self.run_limit, self.window_limit = run_limit, window_limit
        self.interval = max(65, interval)
        self.clock, self.sleep = clock, sleep
        self.run_charged = 0

    def _records(self):
        try:
            rows = [] if not self.path.exists() else [json.loads(l) for l in self.path.read_text(encoding="utf-8").splitlines() if l.strip()]
            reservations, settled = {}, set()
            for row in rows:
                ident = row["id"]
                if row["event"] == "reserve":
                    if ident in reservations or not isinstance(ident, str) or type(row["timestamp"]) not in (int, float) or not math.isfinite(row["timestamp"]):
                        raise ValueError("Invalid reservation")
                    reservations[ident] = {"timestamp": row["timestamp"], "tokens": self.RESERVATION}
                elif row["event"] == "usage":
                    if ident not in reservations or ident in settled or type(row["tokens"]) is not int or row["tokens"] < 0:
                        raise ValueError("Invalid settlement")
                    reservations[ident]["tokens"] = row["tokens"]
                    settled.add(ident)
                else:
                    raise ValueError("Unknown ledger event")
            return list(reservations.values())
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise ProviderError(f"Groq quota ledger cannot be validated ({type(exc).__name__}); no request sent") from None

    def _append(self, record):
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, allow_nan=False) + "\n")

    @contextmanager
    def request(self, estimated_input, max_output, emit):
        if estimated_input + max_output > self.RESERVATION:
            raise ProviderError("Estimated Groq input plus output allowance exceeds 8000 tokens; no request sent or evidence truncated")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.path.with_name(self.path.name + ".lock")
        try:
            handle = lock.open("x", encoding="utf-8")
        except FileExistsError:
            raise ProviderError("Groq ledger is locked by another/interrupted runner; no request sent") from None
        try:
            handle.close()
            records = self._records()
            if records:
                delay = max(0, max(r["timestamp"] for r in records) + self.interval - self.clock())
                if delay:
                    emit("quota_wait", {"provider": "groq", "seconds": delay})
                    # Short sleeps also make cancellation responsive.
                    deadline = self.clock() + delay
                    while self.clock() < deadline:
                        self.sleep(min(30, deadline - self.clock()))
            now = self.clock()
            charged = sum(r["tokens"] for r in records if now - r["timestamp"] < 86400)
            if self.run_charged + self.RESERVATION > self.run_limit or charged + self.RESERVATION > self.window_limit:
                raise ProviderError("Groq local token budget exhausted; no further request sent")
            ident = uuid4().hex
            self._append({"event": "reserve", "id": ident, "timestamp": now, "estimated_input_tokens": estimated_input,
                          "max_output_tokens": max_output, "reserved_tokens": self.RESERVATION})
            self.run_charged += self.RESERVATION
            emit("quota_reserved", {"provider": "groq", "request_id": ident, "reserved_tokens": self.RESERVATION,
                                    "estimated_input_tokens": estimated_input, "run_charged_tokens": self.run_charged,
                                    "window_charged_tokens": charged + self.RESERVATION})
            settled = False

            def settle(tokens):
                nonlocal settled
                if settled or type(tokens) is not int or tokens < 0:
                    raise ProviderError("Invalid Groq usage settlement")
                self._append({"event": "usage", "id": ident, "tokens": tokens})
                self.run_charged += tokens - self.RESERVATION
                settled = True
                emit("quota_usage", {"provider": "groq", "request_id": ident, "reported_total_tokens": tokens,
                                     "run_charged_tokens": self.run_charged})
                if tokens > self.RESERVATION:
                    raise ProviderError("Groq usage exceeded the local per-request reservation; stop and review quotas")
            yield settle
        finally:
            lock.unlink(missing_ok=True)
