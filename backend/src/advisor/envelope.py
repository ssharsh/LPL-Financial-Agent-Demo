"""The response envelope: the one JSON shape every request returns (brief section 7).

The frontend builds against this shape. Do not add, remove, or rename fields without telling the user.
`interpretation`, `verification`, and `declined` are null when they do not apply (always in Phase 1).
`chart` is derived in code from the turn's successful tool results (advisor.charts), or null when none fit.
Every field has no default, so all seven keys must be present in every envelope.

`python -m advisor.envelope` regenerates backend/schema/envelope.schema.json.
"""

import json
from typing import Any

from pydantic import BaseModel, ConfigDict

from advisor.charts import chart_from_ledger
from advisor.config import BACKEND_ROOT
from advisor.tools.ledger import RequestLedger

ENVELOPE_SCHEMA_PATH = BACKEND_ROOT / "schema" / "envelope.schema.json"


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    description: str
    as_of: str


class Chart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    x: str
    y: str
    series: str
    rows: list[dict[str, Any]]


class Verification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    reference_id: str
    verified_at: str


class Declined(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str


class Envelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    interpretation: str | None
    sources: list[Source]
    chart: Chart | None
    log_id: str
    verification: Verification | None
    declined: Declined | None


def envelope_json_schema() -> dict[str, Any]:
    return Envelope.model_json_schema()


def write_schema() -> None:
    ENVELOPE_SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENVELOPE_SCHEMA_PATH.write_text(
        json.dumps(envelope_json_schema(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_envelope(text: str, ledger: RequestLedger, log_id: str) -> Envelope:
    """Phase 1 envelope: sources come only from the ledger's successful tool calls; the chart is derived in
    code from the same calls' results (never from the model). interpretation, verification, and declined
    arrive in later phases and are null."""
    return Envelope(
        text=text,
        interpretation=None,
        sources=[
            Source(type=s.type, description=s.description, as_of=s.as_of.isoformat()) for s in ledger.sources()
        ],
        chart=chart_from_ledger(ledger),
        log_id=log_id,
        verification=None,
        declined=next(
            (
                Declined(reason=str(c.result.get("topic", "")))
                for c in ledger.calls()
                if c.tool == "flag_advice_request" and c.status == "success" and c.result
            ),
            None,
        ),
    )


if __name__ == "__main__":
    write_schema()
    print(f"Wrote {ENVELOPE_SCHEMA_PATH}")
