"""get_performance: dollar results and the linked monthly Modified Dietz time-weighted return (D7)."""

# PROVISIONAL (pending DB teammate): start/end values are portfolio snapshot total_value at calendar
# month-ends; external flows are deposit and withdrawal transactions only (P3).

from datetime import date

from pydantic import BaseModel, ConfigDict, field_validator

from advisor.calc.months import format_month, is_month_end, month_end, parse_month, prev_month
from advisor.calc.performance import (
    FLOW_TYPES,
    RETURN_LABEL,
    ROUNDING_NOTE,
    cents,
    compute_performance,
    percent_2dp,
)
from advisor.data.repository import Repository
from advisor.errors import DataUnavailableError
from advisor.identity import SessionContext
from advisor.tools.common import (
    ToolOutput,
    data_as_of,
    money,
    pct,
    resolve_account_scope,
    snapshot_record_id,
    transaction_record_id,
)
from advisor.tools.ledger import SourceRef

CALCULATION_METHOD = (
    "Monthly Modified Dietz at portfolio level: for each month, BMV and EMV are the sums of the included accounts' "
    "month-end snapshot total_value; external flows are deposits (+) and withdrawals (-); each flow is weighted "
    "w = (D - d) / D where D is the days in the month and d the day of the flow; R = (EMV - BMV - F) / "
    "(BMV + sum(w x flow)). Monthly returns are linked geometrically, unrounded: TWR = product(1 + R) - 1 "
    "(cumulative, not annualized). A month whose denominator is zero or negative has no return, and then the "
    "period has none. investment_gain = end_value - start_value - net_flows."
)


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    start_month: str
    end_month: str
    account_id: int | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def _check_month(cls, value: str) -> str:
        parse_month(value)
        return value


def run(session: SessionContext, repo: Repository, args: Args) -> ToolOutput:
    accounts = resolve_account_scope(session, repo, args.account_id)
    account_ids = [a.account_id for a in accounts]
    as_of = data_as_of(session, repo, accounts)
    start, end = parse_month(args.start_month), parse_month(args.end_month)
    if month_end(*end) > as_of:
        latest = (as_of.year, as_of.month) if is_month_end(as_of) else prev_month((as_of.year, as_of.month))
        raise DataUnavailableError(
            f"end_month {args.end_month} is after the data as-of date {as_of.isoformat()}; latest valid end month "
            f"is {format_month(latest)}."
        )

    values = {(s.account_id, s.snapshot_date): s.total_value for s in repo.list_snapshots(session, account_ids)}
    flows = [
        t
        for t in repo.list_transactions(
            session, account_ids, start_date=date(start[0], start[1], 1), end_date=month_end(*end)
        )
        if t.txn_type in FLOW_TYPES
    ]
    perf = compute_performance(values, flows, start, end, account_ids)

    level = (
        f"account {args.account_id}" if args.account_id is not None else "portfolio (all accounts combined)"
    )
    result = {
        "tool": "get_performance",
        "period": {"start_month": args.start_month, "end_month": args.end_month},
        "scope": {"account_ids": list(perf.account_ids), "level": level},
        "start_value": money(perf.start_value),
        "start_value_date": perf.start_value_date.isoformat(),
        "end_value": money(perf.end_value),
        "end_value_date": perf.end_value_date.isoformat(),
        "net_flows": money(perf.net_flows),
        "investment_gain": money(perf.investment_gain),
        "time_weighted_return_pct": pct(percent_2dp(perf.twr)) if perf.twr is not None else None,
        "return_label": RETURN_LABEL,
        "return_unavailable_reason": perf.return_unavailable_reason,
        "rows": [
            {
                "month": format_month(m.month),
                "begin_value": money(m.begin_value),
                "end_value": money(m.end_value),
                "net_flow": money(m.net_flow),
                "weighted_flow": money(cents(m.weighted_flow)),
                "denominator": money(cents(m.denominator)),
                "monthly_return_pct": (
                    pct(percent_2dp(m.monthly_return)) if m.monthly_return is not None else None
                ),
                "reason": m.reason,
            }
            for m in perf.months
        ],
        "rounding": ROUNDING_NOTE,
    }
    sources = [
        SourceRef(
            type="portfolio_snapshot",
            description=(
                f"Month-end portfolio snapshots {perf.start_value_date.isoformat()} to "
                f"{perf.end_value_date.isoformat()}"
            ),
            as_of=perf.end_value_date,
            record_ids=tuple(snapshot_record_id(a, d) for a, d in perf.snapshot_keys),
        ),
        SourceRef(
            type="transaction",
            description=(
                f"Deposit and withdrawal transactions {date(start[0], start[1], 1).isoformat()} to "
                f"{month_end(*end).isoformat()}"
            ),
            as_of=perf.end_value_date,
            record_ids=tuple(transaction_record_id(t) for t in perf.flow_transaction_ids),
        ),
    ]
    return ToolOutput(result=result, sources=sources, calculation_method=CALCULATION_METHOD)
