"""get_holdings: positions, cash, and values for the session client's accounts (D5)."""

# PROVISIONAL (pending DB teammate): current positions come from the holdings table plus accounts.cash_balance,
# valued at the close on data_as_of; a past month-end (as_of_month) is derived from cumulative buy/sell
# quantities and cash from transactions, valued at that month-end's close. A missing close is an error (never
# another date's price). Assumes snapshot total_value includes cash (P4).

from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from advisor.calc.months import format_month, is_month_end, month_end, parse_month
from advisor.calc.positions import derive_cash, derive_positions
from advisor.data.models import Account
from advisor.data.repository import Repository
from advisor.errors import DataUnavailableError
from advisor.identity import SessionContext
from advisor.tools.common import (
    ToolOutput,
    account_record_id,
    data_as_of,
    holding_record_id,
    money,
    price,
    price_record_id,
    quantity,
    resolve_account_scope,
    transaction_record_id,
    weight_pct,
)
from advisor.tools.ledger import SourceRef

CURRENT_BASIS = "current holdings records"
CALCULATION_METHOD = (
    "market_value = quantity x close_price on price_date, rounded to the cent. total_value = securities_value + "
    "cash. weight_pct = value / total_value (including cash) x 100, rounded half-even to 2 decimal places. "
    "Totals by account, security, and asset class are exact sums of the rounded market values."
)
_ZERO = Decimal("0")


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    as_of_month: str | None = None
    account_id: int | None = None

    @field_validator("as_of_month")
    @classmethod
    def _check_month(cls, value: str | None) -> str | None:
        if value is not None:
            parse_month(value)
        return value


def _valid_month_range(session: SessionContext, repo: Repository, accounts: list[Account]) -> tuple[str, str]:
    """First and last month-end on which every included account has a snapshot."""
    common: set[date] | None = None
    for account in accounts:
        dates = {
            s.snapshot_date
            for s in repo.list_snapshots(session, [account.account_id])
            if is_month_end(s.snapshot_date)
        }
        common = dates if common is None else common & dates
    if not common:
        raise DataUnavailableError("No month-end on which every included account has a portfolio snapshot.")
    first, last = min(common), max(common)
    return format_month((first.year, first.month)), format_month((last.year, last.month))


def run(session: SessionContext, repo: Repository, args: Args) -> ToolOutput:
    accounts = resolve_account_scope(session, repo, args.account_id)
    account_ids = [a.account_id for a in accounts]
    as_of = data_as_of(session, repo, accounts)
    sources: list[SourceRef] = []

    if args.as_of_month is None:
        valuation_date = as_of
        basis = CURRENT_BASIS
        holdings = repo.list_holdings(session, account_ids)
        positions = {(h.account_id, h.security_id): h.quantity for h in holdings}
        cost = {(h.account_id, h.security_id): (h.avg_cost_basis, h.first_purchased) for h in holdings}
        cash = {a.account_id: a.cash_balance for a in accounts}
        sources.append(
            SourceRef(
                type="holding",
                description="Current holdings records",
                as_of=as_of,
                record_ids=tuple(holding_record_id(h.holding_id) for h in holdings),
            )
        )
        account_description = "Account records (current cash balance)"
    else:
        month = parse_month(args.as_of_month)
        valuation_date = month_end(*month)
        first_valid, last_valid = _valid_month_range(session, repo, accounts)
        if valuation_date > as_of:
            raise DataUnavailableError(
                f"as_of_month {args.as_of_month} is after the data as-of date {as_of.isoformat()}; valid months "
                f"are {first_valid} through {last_valid}."
            )
        snapshot_ids = {
            s.account_id for s in repo.list_snapshots(session, account_ids, valuation_date, valuation_date)
        }
        missing = [a for a in account_ids if a not in snapshot_ids]
        if missing:
            raise DataUnavailableError(
                f"No portfolio snapshot for account(s) {', '.join(map(str, missing))} on "
                f"{valuation_date.isoformat()}; valid months are {first_valid} through {last_valid}."
            )
        basis = f"derived from buy and sell transactions through {valuation_date.isoformat()}"
        txns = repo.list_transactions(session, account_ids, end_date=valuation_date)
        positions = derive_positions(txns, valuation_date)
        cost = {}
        cash = derive_cash(txns, valuation_date, account_ids)
        sources.append(
            SourceRef(
                type="transaction",
                description=f"Transactions through {valuation_date.isoformat()} (positions and cash derived)",
                as_of=valuation_date,
                record_ids=tuple(transaction_record_id(t.transaction_id) for t in txns),
            )
        )
        account_description = "Account records"

    securities = {s.security_id: s for s in repo.list_securities({sid for _, sid in positions})}
    class_names = {c.asset_class_id: c.name for c in repo.list_asset_classes()}
    keys = sorted(positions)
    closes = repo.get_close_prices({sid for _, sid in keys}, [valuation_date])
    for _, sid in keys:
        if (sid, valuation_date) not in closes:
            raise DataUnavailableError(
                f"No close price for {securities[sid].ticker} on {valuation_date.isoformat()}."
            )

    market_values = {
        k: (positions[k] * closes[(k[1], valuation_date)]).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
        for k in keys
    }
    securities_value = sum(market_values.values(), _ZERO)
    cash_total = sum((cash[a] for a in account_ids), _ZERO)
    total_value = securities_value + cash_total

    rows = []
    for key in keys:
        account_id, sid = key
        security = securities[sid]
        avg_cost, first_purchased = cost.get(key, (None, None))
        rows.append(
            {
                "account_id": account_id,
                "security_id": sid,
                "ticker": security.ticker,
                "name": security.name,
                "asset_class": class_names[security.asset_class_id],
                "quantity": quantity(positions[key]),
                "close_price": price(closes[(sid, valuation_date)]),
                "price_date": valuation_date.isoformat(),
                "market_value": money(market_values[key]),
                "weight_pct": weight_pct(market_values[key], total_value),
                "avg_cost_basis": price(avg_cost) if avg_cost is not None else None,
                "first_purchased": first_purchased.isoformat() if first_purchased is not None else None,
            }
        )
    cash_rows = [
        {"account_id": a, "cash": money(cash[a]), "weight_pct": weight_pct(cash[a], total_value)}
        for a in account_ids
    ]

    by_account = []
    for a in account_ids:
        sec_value = sum((v for (acct, _), v in market_values.items() if acct == a), _ZERO)
        value = sec_value + cash[a]
        by_account.append(
            {
                "account_id": a,
                "securities_value": money(sec_value),
                "cash": money(cash[a]),
                "total_value": money(value),
                "weight_pct": weight_pct(value, total_value),
            }
        )
    by_security = []
    for sid in sorted({sid for _, sid in keys}):
        units = sum((positions[k] for k in keys if k[1] == sid), _ZERO)
        value = sum((market_values[k] for k in keys if k[1] == sid), _ZERO)
        by_security.append(
            {
                "security_id": sid,
                "ticker": securities[sid].ticker,
                "quantity": quantity(units),
                "market_value": money(value),
                "weight_pct": weight_pct(value, total_value),
            }
        )
    by_asset_class = []
    for class_id in sorted({securities[sid].asset_class_id for _, sid in keys}):
        value = sum((market_values[k] for k in keys if securities[k[1]].asset_class_id == class_id), _ZERO)
        by_asset_class.append(
            {
                "asset_class": class_names[class_id],
                "market_value": money(value),
                "weight_pct": weight_pct(value, total_value),
            }
        )

    result = {
        "tool": "get_holdings",
        "as_of_date": valuation_date.isoformat(),
        "data_as_of": as_of.isoformat(),
        "position_basis": basis,
        "scope": {"account_ids": account_ids},
        "rows": rows,
        "cash": cash_rows,
        "totals": {
            "securities_value": money(securities_value),
            "cash": money(cash_total),
            "total_value": money(total_value),
            "cash_weight_pct": weight_pct(cash_total, total_value),
            "by_account": by_account,
            "by_security": by_security,
            "by_asset_class": by_asset_class,
        },
    }
    sources.append(
        SourceRef(
            type="security_price",
            description=f"Closing prices on {valuation_date.isoformat()}",
            as_of=valuation_date,
            record_ids=tuple(price_record_id(sid, valuation_date) for sid in sorted({s for _, s in keys})),
        )
    )
    sources.append(
        SourceRef(
            type="account",
            description=account_description,
            as_of=as_of if args.as_of_month is None else valuation_date,
            record_ids=tuple(account_record_id(a) for a in account_ids),
        )
    )
    return ToolOutput(result=result, sources=sources, calculation_method=CALCULATION_METHOD)
