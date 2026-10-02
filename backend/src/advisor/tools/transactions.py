"""get_transactions: the session client's transactions in an inclusive date range (D17: unbounded rows)."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from advisor.calc.cash_model import cash_effect
from advisor.calc.months import parse_iso_date
from advisor.data.models import TXN_TYPES, TxnType
from advisor.data.repository import Repository
from advisor.errors import DataUnavailableError
from advisor.identity import SessionContext
from advisor.tools.common import (
    ToolOutput,
    data_as_of,
    money,
    price,
    quantity,
    resolve_account_scope,
    transaction_record_id,
)
from advisor.tools.ledger import SourceRef

CALCULATION_METHOD = (
    "Listed transactions with start_date <= txn_date <= end_date, sorted by (txn_date, transaction_id). amount is "
    "the stored positive magnitude; cash_effect is signed by type (deposit, sell, dividend +; withdrawal, buy, "
    "fee -). Totals are exact sums of the rows."
)
_ZERO = Decimal("0")


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    start_date: str
    end_date: str
    txn_type: TxnType | None = None
    account_id: int | None = None

    @field_validator("start_date", "end_date")
    @classmethod
    def _check_date(cls, value: str) -> str:
        parse_iso_date(value)
        return value

    @model_validator(mode="after")
    def _check_order(self) -> "Args":
        if parse_iso_date(self.start_date) > parse_iso_date(self.end_date):
            raise ValueError(f"start_date {self.start_date} is after end_date {self.end_date}")
        return self


def run(session: SessionContext, repo: Repository, args: Args) -> ToolOutput:
    accounts = resolve_account_scope(session, repo, args.account_id)
    account_ids = [a.account_id for a in accounts]
    as_of = data_as_of(session, repo, accounts)
    start, end = parse_iso_date(args.start_date), parse_iso_date(args.end_date)
    if end > as_of:
        raise DataUnavailableError(
            f"end_date {args.end_date} is after the data as-of date {as_of.isoformat()}; use an end_date on or "
            f"before {as_of.isoformat()}."
        )

    txns = [
        t
        for t in repo.list_transactions(session, account_ids, start_date=start, end_date=end)
        if args.txn_type is None or t.txn_type == args.txn_type
    ]
    txns.sort(key=lambda t: (t.txn_date, t.transaction_id))
    tickers = {
        s.security_id: s.ticker
        for s in repo.list_securities({t.security_id for t in txns if t.security_id is not None})
    }

    rows = []
    net = _ZERO
    by_type: dict[str, tuple[int, Decimal]] = {}
    for txn in txns:
        effect = cash_effect(txn)
        net += effect
        count, total = by_type.get(txn.txn_type, (0, _ZERO))
        by_type[txn.txn_type] = (count + 1, total + txn.amount)
        rows.append(
            {
                "transaction_id": txn.transaction_id,
                "account_id": txn.account_id,
                "txn_date": txn.txn_date.isoformat(),
                "txn_type": txn.txn_type,
                "security_id": txn.security_id,
                "ticker": tickers[txn.security_id] if txn.security_id is not None else None,
                "quantity": quantity(txn.quantity) if txn.quantity is not None else None,
                "price": price(txn.price) if txn.price is not None else None,
                "amount": money(txn.amount),
                "cash_effect": money(effect),
            }
        )

    result = {
        "tool": "get_transactions",
        "period": {"start_date": args.start_date, "end_date": args.end_date},
        "filters": {"txn_type": args.txn_type, "account_ids": account_ids},
        "data_as_of": as_of.isoformat(),
        "rows": rows,
        "totals": {
            "count": len(rows),
            "by_type": [
                {"txn_type": t, "count": by_type[t][0], "total_amount": money(by_type[t][1])}
                for t in TXN_TYPES
                if t in by_type
            ],
            "net_cash_effect": money(net),
        },
    }
    description = f"Transactions {args.start_date} to {args.end_date}"
    if args.txn_type is not None:
        description += f" (type {args.txn_type})"
    if args.account_id is not None:
        description += f" (account {args.account_id})"
    sources = [
        SourceRef(
            type="transaction",
            description=description,
            as_of=end,
            record_ids=tuple(transaction_record_id(t.transaction_id) for t in txns),
        )
    ]
    return ToolOutput(result=result, sources=sources, calculation_method=CALCULATION_METHOD)
