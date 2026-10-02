import json
from datetime import date

import pytest
from jsonschema import Draft202012Validator

from advisor.envelope import ENVELOPE_SCHEMA_PATH, Envelope, build_envelope, envelope_json_schema
from advisor.tools.ledger import RequestLedger, SourceRef

ENVELOPE_KEYS = {"text", "interpretation", "sources", "chart", "log_id", "verification", "declined"}


def phase1_envelope() -> dict:
    return {
        "text": "Your accounts were worth $100.00.",
        "interpretation": None,
        "sources": [{"type": "account", "description": "Accounts", "as_of": "2026-09-30"}],
        "chart": None,
        "log_id": "log_abc",
        "verification": None,
        "declined": None,
    }


def full_envelope() -> dict:
    return {
        "text": "t",
        "interpretation": "i",
        "sources": [{"type": "transaction", "description": "d", "as_of": "2026-09-30"}],
        "chart": {"type": "line", "x": "month", "y": "value", "series": "account", "rows": [{"month": "2026-09"}]},
        "log_id": "log_1",
        "verification": {"status": "verified", "reference_id": "ref_1", "verified_at": "2026-10-01T00:00:00Z"},
        "declined": {"reason": "r"},
    }


@pytest.fixture(scope="module")
def validator():
    return Draft202012Validator(json.loads(ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8")))


def test_committed_schema_matches_model():
    expected = json.dumps(envelope_json_schema(), indent=2, sort_keys=True) + "\n"
    assert ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8") == expected, (
        "schema/envelope.schema.json is stale: run `PYTHONPATH=src .venv/bin/python -m advisor.envelope`"
    )


def test_schema_requires_all_seven_keys():
    schema = envelope_json_schema()
    assert set(schema["required"]) == ENVELOPE_KEYS
    assert set(schema["properties"]) == ENVELOPE_KEYS


def test_valid_envelopes(validator):
    validator.validate(phase1_envelope())
    validator.validate(full_envelope())
    Envelope.model_validate(phase1_envelope())
    Envelope.model_validate(full_envelope())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda e: e.pop("log_id"),
        lambda e: e.pop("interpretation"),
        lambda e: e.update(extra="x"),
        lambda e: e["sources"][0].update(record_ids=["1"]),
        lambda e: e["sources"][0].pop("as_of"),
    ],
    ids=["missing log_id", "missing interpretation", "extra key", "extra source key", "source missing as_of"],
)
def test_invalid_envelopes(validator, mutate):
    env = phase1_envelope()
    mutate(env)
    assert list(validator.iter_errors(env)), "expected a schema validation error"


def test_build_envelope_uses_ledger_sources_and_nulls():
    ledger = RequestLedger()
    ledger.record(
        tool="get_accounts",
        arguments={},
        status="success",
        result={"tool": "get_accounts"},
        sources=(SourceRef("account", "Accounts", date(2026, 9, 30), ("101",)),),
        calculation_method="m",
    )
    ledger.record(tool="get_holdings", arguments={"account_id": 104}, status="error", error="no access")
    env = build_envelope("hello", ledger, "log_x")
    assert env.text == "hello"
    assert env.log_id == "log_x"
    assert [s.model_dump() for s in env.sources] == [
        {"type": "account", "description": "Accounts", "as_of": "2026-09-30"}
    ]
    assert env.interpretation is None
    assert env.chart is None
    assert env.verification is None
    assert env.declined is None
    dumped = json.loads(env.model_dump_json())
    assert set(dumped) == ENVELOPE_KEYS
