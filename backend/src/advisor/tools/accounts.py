"""get_accounts: the session client's accounts with cash and latest snapshot value (D6)."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from advisor.data.repository import Repository
from advisor.errors import DataUnavailableError
from advisor.identity import SessionContext
from advisor.tools.common import (
    ToolOutput,
    account_record_id,
    data_as_of,
    money,
    resolve_account_scope,
    snapshot_record_id,
)
from advisor.tools.ledger import SourceRef

CALCULATION_METHOD = (
    "Listed the client's accounts from account records. cash_balance is the current account record (stated as of "
    "data_as_of); total_value is each account's latest portfolio snapshot. Totals are exact sums of the rows."
)


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def run(session: SessionContext, repo: Repository, args: Args) -> ToolOutput:
    accounts = resolve_account_scope(session, repo, None)
    as_of = data_as_of(session, repo, accounts)
    latest = {}
    for snap in repo.list_snapshots(session, [a.account_id for a in accounts]):
        current = latest.get(snap.account_id)
        if current is None or snap.snapshot_date > current.snapshot_date:
            latest[snap.account_id] = snap

    rows = []
    total_cash = Decimal("0")
    total_value = Decimal("0")
    for account in accounts:
        snap = latest.get(account.account_id)
        if snap is None:
            raise DataUnavailableError(f"Account {account.account_id} has no portfolio snapshots.")
        total_cash += account.cash_balance
        total_value += snap.total_value
        rows.append(
            {
                "account_id": account.account_id,
                "account_type": account.account_type,
                "account_name": account.account_name,
                "opened_date": account.opened_date.isoformat(),
                "objective": account.objective,
                "cash_balance": money(account.cash_balance),
                "total_value": money(snap.total_value),
                "total_value_date": snap.snapshot_date.isoformat(),
            }
        )

    result = {
        "tool": "get_accounts",
        "data_as_of": as_of.isoformat(),
        "rows": rows,
        "totals": {
            "account_count": len(rows),
            "cash_balance": money(total_cash),
            "total_value": money(total_value),
        },
    }
    used = [latest[a.account_id] for a in accounts]
    sources = [
        SourceRef(
            type="account",
            description="Account records (type, name, objective, cash balance)",
            as_of=as_of,
            record_ids=tuple(account_record_id(a.account_id) for a in accounts),
        ),
        SourceRef(
            type="portfolio_snapshot",
            description="Latest portfolio snapshot per account",
            as_of=max(s.snapshot_date for s in used),
            record_ids=tuple(snapshot_record_id(s.account_id, s.snapshot_date) for s in used),
        ),
    ]
    return ToolOutput(result=result, sources=sources, calculation_method=CALCULATION_METHOD)
