"""Readable log and audit store (brief section 8).

The log record is built only from structured data the code already holds: the session, the question, the request
ledger (each tool call with validated arguments, records used with as-of dates, calculation method, result, and
SHA-256), the answer text, and the guardrail results. The human-readable form is rendered by a fixed code
template. The model writes no part of either.

Both forms are stored under a key prefix that starts with the client ID. Phase 1 keeps them in memory; the S3
store with Object Lock arrives in Phase 5.
"""

import hashlib
import json
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from advisor.config import ChatSettings
from advisor.errors import ConfigError, IdentityError, LogNotFoundError, PhaseNotAvailableError
from advisor.identity import SessionContext
from advisor.tools.common import canonical_json, sha256_hex
from advisor.tools.ledger import RequestLedger

OFFICIAL_RECORD_LINE = "The account statement remains the official record."
GUARDRAILS_PHASE1 = {
    "results": [],
    "note": "Guardrails arrive in Phase 5; no guardrail checks ran for this exchange.",
}

_LOG_ID_RE = re.compile(r"^log_[0-9a-f]{32}$")


def new_log_id() -> str:
    # D11: application log ID. The teammate's chat_log_exports.log_id is SERIAL; reconcile in Phase 5.
    return "log_" + uuid.uuid4().hex


# -- log record ---------------------------------------------------------------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoggedSource(_Strict):
    type: str
    description: str
    as_of: str
    record_ids: list[str]


class LoggedToolCall(_Strict):
    sequence: int
    tool: str
    arguments: dict[str, Any]
    status: Literal["success", "error"]
    calculation_method: str | None
    sources: list[LoggedSource]
    result: dict[str, Any] | None
    result_sha256: str | None
    error: str | None


class RecordUsed(_Strict):
    type: str
    as_of: str
    record_ids: list[str]


class GuardrailReport(_Strict):
    results: list[dict[str, Any]]
    note: str


class LogRecord(_Strict):
    log_id: str
    created_at: str  # UTC, ISO 8601
    client_id: int
    advisor_id: int
    model_id: str
    question: str
    interpretation: str | None  # None in Phase 1
    tool_calls: list[LoggedToolCall]
    records_used: list[RecordUsed]
    results_sha256: str  # SHA-256 of canonical JSON of the list of successful results, in call order
    answer_text: str
    guardrails: GuardrailReport
    official_record_note: str


def build_log_record(
    session: SessionContext,
    *,
    log_id: str,
    question: str,
    answer_text: str,
    ledger: RequestLedger,
    model_id: str,
    now: datetime | None = None,
) -> LogRecord:
    """Assemble the log record from code data only."""
    created = now if now is not None else datetime.now(timezone.utc)
    if created.tzinfo is None:
        raise ValueError("Log timestamps must be timezone-aware (UTC)")
    calls = ledger.calls()
    tool_calls = [
        LoggedToolCall(
            sequence=c.sequence,
            tool=c.tool,
            arguments=c.arguments,
            status=c.status,
            calculation_method=c.calculation_method,
            sources=[LoggedSource(**s.to_json()) for s in c.sources],
            result=c.result,
            result_sha256=c.result_sha256,
            error=c.error,
        )
        for c in calls
    ]
    records_used = [
        RecordUsed(type=s.type, as_of=s.as_of.isoformat(), record_ids=list(s.record_ids)) for s in ledger.sources()
    ]
    successful_results = [c.result for c in calls if c.status == "success"]
    return LogRecord(
        log_id=log_id,
        created_at=created.astimezone(timezone.utc).isoformat(),
        client_id=session.client_id,
        advisor_id=session.advisor_id,
        model_id=model_id,
        question=question,
        interpretation=None,
        tool_calls=tool_calls,
        records_used=records_used,
        results_sha256=sha256_hex(successful_results),
        answer_text=answer_text,
        guardrails=GuardrailReport(**GUARDRAILS_PHASE1),
        official_record_note=OFFICIAL_RECORD_LINE,
    )


def record_json(record: LogRecord) -> str:
    """The stored JSON form (canonical JSON)."""
    return canonical_json(record.model_dump(mode="json"))


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# -- human-readable rendering (fixed template) --------------------------------------------------------------


def _indent(text: str, prefix: str) -> list[str]:
    return [prefix + line for line in (text.splitlines() or [""])]


def render_log(record: LogRecord) -> str:
    lines = [
        f"Exchange log {record.log_id}",
        f"Created (UTC): {record.created_at}",
        f"Client ID: {record.client_id}",
        f"Advisor ID: {record.advisor_id}",
        f"Model: {record.model_id}",
        "",
        "Question:",
        *_indent(record.question, "  "),
        "",
        f"Interpretation: {record.interpretation if record.interpretation is not None else 'None'}",
        "",
    ]
    if record.tool_calls:
        lines.append(f"Tool calls ({len(record.tool_calls)}):")
    else:
        lines.append("Tool calls: none")
    for call in record.tool_calls:
        lines.append(f"  {call.sequence}. {call.tool} [{call.status}]")
        lines.append(f"     Arguments: {canonical_json(call.arguments)}")
        if call.status == "success":
            lines.append(f"     Calculation method: {call.calculation_method}")
            lines.append("     Records used:")
            for src in call.sources:
                lines.append(f"       - {src.type} as of {src.as_of}: {src.description}")
                lines.append(f"         IDs: {', '.join(src.record_ids) if src.record_ids else '(none)'}")
            lines.append("     Result:")
            lines.extend(_indent(json.dumps(call.result, indent=2, ensure_ascii=False), "       "))
            lines.append(f"     Result SHA-256: {call.result_sha256}")
        else:
            lines.append(f"     Error: {call.error}")
    lines.append("")
    lines.append("Records used (successful calls):")
    if record.records_used:
        for used in record.records_used:
            lines.append(f"  - {used.type} as of {used.as_of}: {', '.join(used.record_ids) or '(none)'}")
    else:
        lines.append("  none")
    lines += [
        "",
        "Answer:",
        *_indent(record.answer_text, "  "),
        "",
        f"Guardrails: {record.guardrails.note}",
        f"Results SHA-256: {record.results_sha256}",
        "",
        record.official_record_note,
    ]
    return "\n".join(lines) + "\n"


# -- audit store --------------------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StoredLog:
    """Log index entry (brief section 8: log ID, key, hash, timestamp)."""

    log_id: str
    json_key: str
    text_key: str
    record_sha256: str  # SHA-256 of the stored JSON bytes
    stored_at: datetime  # UTC


def log_keys(client_id: int, log_id: str) -> tuple[str, str]:
    prefix = f"{client_id}/logs/{log_id}"
    return prefix + ".json", prefix + ".txt"


class AuditStore(ABC):
    """Every lookup is restricted to the session client's key prefix."""

    @abstractmethod
    def put(self, session: SessionContext, record: LogRecord, rendered: str) -> StoredLog: ...

    @abstractmethod
    def get_record(self, session: SessionContext, log_id: str) -> LogRecord: ...

    @abstractmethod
    def get_rendered(self, session: SessionContext, log_id: str) -> str: ...

    @abstractmethod
    def list_logs(self, session: SessionContext) -> list[StoredLog]: ...


class MemoryAuditStore(AuditStore):
    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._index: dict[int, list[StoredLog]] = {}

    def put(self, session: SessionContext, record: LogRecord, rendered: str) -> StoredLog:
        if record.client_id != session.client_id:
            raise IdentityError(
                f"Log record is for client {record.client_id} but the session is client {session.client_id}"
            )
        if not _LOG_ID_RE.match(record.log_id):
            raise ValueError(f"Invalid log ID {record.log_id!r}")
        json_key, text_key = log_keys(session.client_id, record.log_id)
        if json_key in self._objects:
            raise ValueError(f"Log {record.log_id} already exists; logs are write-once")
        body = record_json(record).encode("utf-8")
        self._objects[json_key] = body
        self._objects[text_key] = rendered.encode("utf-8")
        entry = StoredLog(
            log_id=record.log_id,
            json_key=json_key,
            text_key=text_key,
            record_sha256=sha256_hex_bytes(body),
            stored_at=datetime.now(timezone.utc),
        )
        self._index.setdefault(session.client_id, []).append(entry)
        return entry

    def _get(self, session: SessionContext, log_id: str, which: int) -> bytes:
        not_found = LogNotFoundError(f"Log {log_id} was not found for this client.")
        if not isinstance(log_id, str) or not _LOG_ID_RE.match(log_id):
            raise not_found
        key = log_keys(session.client_id, log_id)[which]
        if key not in self._objects:
            raise not_found
        return self._objects[key]

    def get_record(self, session: SessionContext, log_id: str) -> LogRecord:
        return LogRecord.model_validate_json(self._get(session, log_id, 0))

    def get_rendered(self, session: SessionContext, log_id: str) -> str:
        return self._get(session, log_id, 1).decode("utf-8")

    def list_logs(self, session: SessionContext) -> list[StoredLog]:
        return list(self._index.get(session.client_id, []))


def build_audit_store(settings: ChatSettings) -> AuditStore:
    if settings.audit_backend == "memory":
        return MemoryAuditStore()
    if settings.audit_backend == "s3":
        raise PhaseNotAvailableError(
            "AUDIT_BACKEND=s3: the S3 audit store arrives in Phase 5. Use AUDIT_BACKEND=memory for now."
        )
    raise ConfigError(f"AUDIT_BACKEND={settings.audit_backend!r} is not supported. Allowed value: memory.")
