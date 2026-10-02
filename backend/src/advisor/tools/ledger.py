"""Per-request record of every tool call that reached tool code (success and error)."""

import threading
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal

from advisor.tools.common import sha256_hex


@dataclass(frozen=True, slots=True)
class SourceRef:
    type: str  # account, holding, transaction, portfolio_snapshot, security_price
    description: str
    as_of: date
    record_ids: tuple[str, ...]

    def to_json(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "description": self.description,
            "as_of": self.as_of.isoformat(),
            "record_ids": list(self.record_ids),
        }


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    sequence: int  # 1-based, in call order
    tool: str
    arguments: dict[str, Any]  # validated arguments (raw arguments when validation failed)
    status: Literal["success", "error"]
    result: dict[str, Any] | None
    result_sha256: str | None  # SHA-256 of canonical_json(result)
    sources: tuple[SourceRef, ...]
    calculation_method: str | None
    error: str | None
    called_at: datetime  # UTC


class RequestLedger:
    """Thread-safe: Strands runs tools via asyncio.to_thread."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._calls: list[ToolCallRecord] = []

    def record(
        self,
        *,
        tool: str,
        arguments: dict[str, Any],
        status: Literal["success", "error"],
        result: dict[str, Any] | None = None,
        sources: tuple[SourceRef, ...] = (),
        calculation_method: str | None = None,
        error: str | None = None,
    ) -> ToolCallRecord:
        result_sha256 = sha256_hex(result) if result is not None else None
        with self._lock:
            entry = ToolCallRecord(
                sequence=len(self._calls) + 1,
                tool=tool,
                arguments=dict(arguments),
                status=status,
                result=result,
                result_sha256=result_sha256,
                sources=tuple(sources),
                calculation_method=calculation_method,
                error=error,
                called_at=datetime.now(timezone.utc),
            )
            self._calls.append(entry)
        return entry

    def calls(self) -> tuple[ToolCallRecord, ...]:
        with self._lock:
            return tuple(self._calls)

    def sources(self) -> tuple[SourceRef, ...]:
        """Sources of successful calls, de-duplicated by (type, description, as_of) in first-seen order.
        record_ids of duplicates are merged (ordered union)."""
        merged: dict[tuple[str, str, date], dict[str, None]] = {}
        for call in self.calls():
            if call.status != "success":
                continue
            for src in call.sources:
                ids = merged.setdefault((src.type, src.description, src.as_of), {})
                ids.update(dict.fromkeys(src.record_ids))
        return tuple(SourceRef(t, d, a, tuple(ids)) for (t, d, a), ids in merged.items())
