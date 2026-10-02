import json
from datetime import datetime, timezone

import pytest

from advisor.audit import (
    GUARDRAILS_PHASE1,
    OFFICIAL_RECORD_LINE,
    LogRecord,
    MemoryAuditStore,
    build_audit_store,
    build_log_record,
    new_log_id,
    record_json,
    render_log,
    sha256_hex_bytes,
)
from advisor.config import ChatSettings
from advisor.errors import ConfigError, LogNotFoundError, PhaseNotAvailableError, ToolArgumentError
from advisor.tools.common import canonical_json, sha256_hex
from advisor.tools.factory import build_tools, call_tool
from advisor.tools.ledger import RequestLedger

QUESTION = "How did my accounts do in September 2026?"
ANSWER = "Your accounts had net flows of -$7,700.00."
MODEL_ID = "test-model"
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def ledger_with_calls(session, repo):
    """One successful call and one failed (ownership) call, through the real tools."""
    ledger = RequestLedger()
    tools = build_tools(session, repo, ledger)
    call_tool(tools, "get_performance", {"start_month": "2026-09", "end_month": "2026-09"})
    with pytest.raises(ToolArgumentError):
        call_tool(tools, "get_holdings", {"account_id": 101})
    return ledger


@pytest.fixture
def client2(session_for, seed_repo):
    session = session_for(2)
    ledger = ledger_with_calls(session, seed_repo)
    record = build_log_record(
        session,
        log_id=new_log_id(),
        question=QUESTION,
        answer_text=ANSWER,
        ledger=ledger,
        model_id=MODEL_ID,
        now=NOW,
    )
    return session, ledger, record


def test_canonical_json():
    assert canonical_json({"b": "1.00", "a": [1, 2]}) == '{"a":[1,2],"b":"1.00"}'


def test_log_record_contents(client2):
    session, ledger, record = client2
    calls = ledger.calls()
    assert record.client_id == 2 and record.advisor_id == session.advisor_id
    assert record.question == QUESTION
    assert record.answer_text == ANSWER
    assert record.model_id == MODEL_ID
    assert record.interpretation is None
    assert record.created_at == "2026-10-01T12:00:00+00:00"
    assert record.guardrails.model_dump() == GUARDRAILS_PHASE1
    assert record.official_record_note == OFFICIAL_RECORD_LINE

    ok, err = record.tool_calls
    assert ok.tool == "get_performance" and ok.status == "success"
    assert ok.arguments == {"start_month": "2026-09", "end_month": "2026-09", "account_id": None}
    assert ok.result == calls[0].result
    assert ok.result["net_flows"] == "-7700.00"
    assert ok.result_sha256 == sha256_hex(calls[0].result)
    assert ok.calculation_method == calls[0].calculation_method and ok.calculation_method
    assert {s.type for s in ok.sources} == {"portfolio_snapshot", "transaction"}
    assert all(s.as_of == "2026-09-30" and s.record_ids for s in ok.sources)

    assert err.tool == "get_holdings" and err.status == "error"
    assert err.arguments["account_id"] == 101
    assert err.result is None and err.result_sha256 is None
    assert "101" in err.error

    assert [(r.type, r.as_of) for r in record.records_used] == [
        (s.type, s.as_of.isoformat()) for s in ledger.sources()
    ]
    assert record.results_sha256 == sha256_hex([calls[0].result])


def test_log_record_rejects_unknown_fields(client2):
    _, _, record = client2
    data = record.model_dump(mode="json")
    data["extra"] = "x"
    with pytest.raises(ValueError):
        LogRecord.model_validate(data)


def test_rendered_log(client2):
    _, _, record = client2
    text = render_log(record)
    assert text.rstrip("\n").splitlines()[-1] == OFFICIAL_RECORD_LINE
    assert QUESTION in text
    assert ANSWER in text
    for call in record.tool_calls:
        assert call.tool in text
        if call.result_sha256:
            assert call.result_sha256 in text
    assert record.results_sha256 in text
    assert record.tool_calls[0].calculation_method in text
    assert "as of 2026-09-30" in text
    assert GUARDRAILS_PHASE1["note"] in text
    assert "Interpretation: None" in text


def test_rendered_log_without_tool_calls(session_for):
    record = build_log_record(
        session_for(1), log_id=new_log_id(), question="hi", answer_text="hello",
        ledger=RequestLedger(), model_id=MODEL_ID, now=NOW,
    )
    text = render_log(record)
    assert "Tool calls: none" in text
    assert text.rstrip("\n").endswith(OFFICIAL_RECORD_LINE)


def test_store_keys_isolation_and_listing(client2, session_for, seed_repo):
    session2, _, record2 = client2
    store = MemoryAuditStore()
    stored = store.put(session2, record2, render_log(record2))
    assert stored.json_key == f"2/logs/{record2.log_id}.json"
    assert stored.text_key == f"2/logs/{record2.log_id}.txt"
    assert stored.record_sha256 == sha256_hex_bytes(record_json(record2).encode("utf-8"))

    session1 = session_for(1)
    record1 = build_log_record(
        session1, log_id=new_log_id(), question="q", answer_text="a",
        ledger=RequestLedger(), model_id=MODEL_ID, now=NOW,
    )
    store.put(session1, record1, render_log(record1))

    assert store.get_record(session2, record2.log_id) == record2
    assert store.get_rendered(session2, record2.log_id) == render_log(record2)
    with pytest.raises(LogNotFoundError):
        store.get_record(session1, record2.log_id)
    with pytest.raises(LogNotFoundError):
        store.get_rendered(session1, record2.log_id)
    with pytest.raises(LogNotFoundError):
        store.get_record(session1, f"../2/logs/{record2.log_id}")
    assert [s.log_id for s in store.list_logs(session2)] == [record2.log_id]
    assert [s.log_id for s in store.list_logs(session1)] == [record1.log_id]


def test_store_rejects_foreign_record_and_overwrite(client2, session_for):
    session2, _, record2 = client2
    store = MemoryAuditStore()
    with pytest.raises(Exception, match="client 2"):
        store.put(session_for(1), record2, render_log(record2))
    store.put(session2, record2, render_log(record2))
    with pytest.raises(ValueError, match="write-once"):
        store.put(session2, record2, render_log(record2))


def test_record_sha256_is_stable(client2):
    session2, _, record2 = client2
    a = MemoryAuditStore().put(session2, record2, render_log(record2))
    b = MemoryAuditStore().put(session2, record2, render_log(record2))
    assert a.record_sha256 == b.record_sha256
    assert json.loads(record_json(record2))["log_id"] == record2.log_id


def test_build_audit_store():
    base = dict(data_backend="memory", aws_region="r", bedrock_model_id="m")
    assert isinstance(build_audit_store(ChatSettings(audit_backend="memory", **base)), MemoryAuditStore)
    with pytest.raises(PhaseNotAvailableError, match="Phase 5"):
        build_audit_store(ChatSettings(audit_backend="s3", **base))
    with pytest.raises(ConfigError):
        build_audit_store(ChatSettings(audit_backend="disk", **base))
