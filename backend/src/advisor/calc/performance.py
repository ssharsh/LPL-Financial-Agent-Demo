"""Time-weighted return: monthly Modified Dietz, linked geometrically. Pure math, no I/O.

All arithmetic runs under decimal.localcontext(prec=28, rounding=ROUND_HALF_EVEN). Monthly returns are kept
unrounded and linked; rounding happens only for display (see ROUNDING_NOTE). A simple percent change
(end / start - 1) is never computed here or anywhere else.
"""

# PROVISIONAL (pending DB teammate): start/end values are portfolio_snapshots.total_value (one row per account
# per calendar month-end) and external flows are deposit (= the brief's contribution) and withdrawal
# transactions only (P3).

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from advisor.calc.months import (
    Month,
    days_in_month,
    format_month,
    is_month_end,
    iter_months,
    month_end,
    next_month,
    prev_month,
)
from advisor.data.models import Transaction
from advisor.errors import DataUnavailableError, ToolArgumentError

RETURN_LABEL = "time-weighted return (monthly Modified Dietz, linked)"
ROUNDING_NOTE = (
    "Dollar amounts are exact to the cent. Monthly returns are computed with Decimal (28 significant digits) "
    "and linked unrounded; percentages are rounded half-even to 2 decimal places for display."
)
FLOW_TYPES = ("deposit", "withdrawal")

_PRECISION = 28
_ZERO = Decimal("0")
_ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class MonthResult:
    month: Month
    begin_date: date
    end_date: date
    begin_value: Decimal
    end_value: Decimal
    net_flow: Decimal
    weighted_flow: Decimal  # unrounded
    denominator: Decimal  # unrounded
    monthly_return: Decimal | None  # unrounded fraction (0.047 = 4.7%); None when the denominator is <= 0
    reason: str | None


@dataclass(frozen=True, slots=True)
class PerformanceResult:
    start_month: Month
    end_month: Month
    account_ids: tuple[int, ...]
    start_value: Decimal
    start_value_date: date
    end_value: Decimal
    end_value_date: date
    net_flows: Decimal
    investment_gain: Decimal
    twr: Decimal | None  # unrounded cumulative fraction; None when any month's return is undefined
    return_unavailable_reason: str | None
    months: tuple[MonthResult, ...]
    snapshot_keys: tuple[tuple[int, date], ...]  # (account_id, snapshot_date) of every snapshot used
    flow_transaction_ids: tuple[int, ...]  # deposit/withdrawal transactions used, in (txn_date, id) order


def cents(value: Decimal) -> Decimal:
    """Round to 0.01, half-even (display only)."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return value.quantize(Decimal("0.01"))


def percent_2dp(fraction: Decimal) -> Decimal:
    """A return fraction as a percentage rounded half-even to 2 decimal places (display only)."""
    with localcontext() as ctx:
        ctx.prec = _PRECISION
        ctx.rounding = ROUND_HALF_EVEN
        return (fraction * 100).quantize(Decimal("0.01"))


def denominator_reason(month: Month) -> str:
    return f"Modified Dietz denominator is zero or negative for {format_month(month)}"


def _flow_amount(txn: Transaction) -> Decimal:
    match txn.txn_type:
        case "deposit":
            return txn.amount
        case "withdrawal":
            return -txn.amount
        case _:
            raise ValueError(f"Transaction {txn.transaction_id} ({txn.txn_type}) is not an external flow")


def _check_coverage(
    snapshot_values: Mapping[tuple[int, date], Decimal],
    account_ids: tuple[int, ...],
    start_month: Month,
    end_month: Month,
) -> None:
    """Every account needs a snapshot at every month-end from the month before start through end."""
    required = [month_end(*m) for m in iter_months(prev_month(start_month), end_month)]
    month_end_dates: dict[int, list[date]] = {}
    for account_id in account_ids:
        dates = sorted(d for (a, d) in snapshot_values if a == account_id and is_month_end(d))
        if not dates:
            raise DataUnavailableError(f"Account {account_id} has no month-end portfolio snapshots.")
        month_end_dates[account_id] = dates

    earliest_start = next_month(max((d[0].year, d[0].month) for d in month_end_dates.values()))
    latest_end = min((d[-1].year, d[-1].month) for d in month_end_dates.values())

    start_date = required[0]
    for account_id in account_ids:
        if (account_id, start_date) not in snapshot_values:
            if start_date < month_end_dates[account_id][0]:
                raise DataUnavailableError(
                    f"No portfolio snapshot for account {account_id} on {start_date.isoformat()} (needed as the "
                    f"starting value for {format_month(start_month)}); earliest valid start month is "
                    f"{format_month(earliest_start)}."
                )
            raise DataUnavailableError(
                f"No portfolio snapshot for account {account_id} on {start_date.isoformat()} (needed as the "
                f"starting value for {format_month(start_month)})."
            )
    end_date = required[-1]
    for account_id in account_ids:
        if (account_id, end_date) not in snapshot_values:
            if end_date > month_end_dates[account_id][-1]:
                raise DataUnavailableError(
                    f"No portfolio snapshot for account {account_id} on {end_date.isoformat()} (needed as the "
                    f"ending value for {format_month(end_month)}); latest valid end month is "
                    f"{format_month(latest_end)}."
                )
            raise DataUnavailableError(
                f"No portfolio snapshot for account {account_id} on {end_date.isoformat()} (needed as the "
                f"ending value for {format_month(end_month)})."
            )
    for day in required[1:-1]:
        for account_id in account_ids:
            if (account_id, day) not in snapshot_values:
                raise DataUnavailableError(
                    f"No portfolio snapshot for account {account_id} on {day.isoformat()} (month-end inside the "
                    f"requested period)."
                )


def compute_performance(
    snapshot_values: Mapping[tuple[int, date], Decimal],
    transactions: Iterable[Transaction],
    start_month: Month,
    end_month: Month,
    account_ids: Iterable[int],
) -> PerformanceResult:
    """Portfolio-level monthly Modified Dietz return over [start_month, end_month] for the account set.

    snapshot_values: total_value per (account_id, snapshot_date). transactions: may include any type; only
    deposit (+) and withdrawal (-) transactions of the given accounts are external flows. No interpolation and
    no zero-substitution: a missing month-end snapshot is an error.
    """
    if start_month > end_month:
        raise ToolArgumentError(
            f"start_month {format_month(start_month)} is after end_month {format_month(end_month)}."
        )
    accounts = tuple(sorted(set(account_ids)))
    if not accounts:
        raise ToolArgumentError("At least one account is required.")
    _check_coverage(snapshot_values, accounts, start_month, end_month)

    period_start = date(start_month[0], start_month[1], 1)
    period_end = month_end(*end_month)
    flows = sorted(
        (
            t
            for t in transactions
            if t.account_id in accounts
            and t.txn_type in FLOW_TYPES
            and period_start <= t.txn_date <= period_end
        ),
        key=lambda t: (t.txn_date, t.transaction_id),
    )

    with localcontext() as ctx:
        ctx.prec = _PRECISION
        ctx.rounding = ROUND_HALF_EVEN

        months: list[MonthResult] = []
        snapshot_keys: list[tuple[int, date]] = []
        for month in iter_months(start_month, end_month):
            begin_date = month_end(*prev_month(month))
            end_date = month_end(*month)
            if not snapshot_keys:
                snapshot_keys.extend((a, begin_date) for a in accounts)
            snapshot_keys.extend((a, end_date) for a in accounts)

            bmv = sum((snapshot_values[(a, begin_date)] for a in accounts), _ZERO)
            emv = sum((snapshot_values[(a, end_date)] for a in accounts), _ZERO)
            total_days = days_in_month(*month)
            net_flow = _ZERO
            weighted_flow = _ZERO
            for txn in flows:
                if (txn.txn_date.year, txn.txn_date.month) != month:
                    continue
                amount = _flow_amount(txn)
                weight = Decimal(total_days - txn.txn_date.day) / Decimal(total_days)
                net_flow += amount
                weighted_flow += weight * amount
            denominator = bmv + weighted_flow
            if denominator <= _ZERO:
                monthly_return, reason = None, denominator_reason(month)
            else:
                monthly_return, reason = (emv - bmv - net_flow) / denominator, None
            months.append(
                MonthResult(
                    month=month,
                    begin_date=begin_date,
                    end_date=end_date,
                    begin_value=bmv,
                    end_value=emv,
                    net_flow=net_flow,
                    weighted_flow=weighted_flow,
                    denominator=denominator,
                    monthly_return=monthly_return,
                    reason=reason,
                )
            )

        unavailable = [m.month for m in months if m.monthly_return is None]
        if unavailable:
            twr = None
            unavailable_reason = (
                "Modified Dietz denominator is zero or negative for "
                f"{', '.join(format_month(m) for m in unavailable)}, so the time-weighted return for this "
                "period cannot be computed."
            )
        else:
            growth = _ONE
            for m in months:
                growth *= _ONE + m.monthly_return
            twr = growth - _ONE
            unavailable_reason = None

        start_value = months[0].begin_value
        end_value = months[-1].end_value
        net_flows = sum((_flow_amount(t) for t in flows), _ZERO)
        investment_gain = end_value - start_value - net_flows

    return PerformanceResult(
        start_month=start_month,
        end_month=end_month,
        account_ids=accounts,
        start_value=start_value,
        start_value_date=months[0].begin_date,
        end_value=end_value,
        end_value_date=months[-1].end_date,
        net_flows=net_flows,
        investment_gain=investment_gain,
        twr=twr,
        return_unavailable_reason=unavailable_reason,
        months=tuple(months),
        snapshot_keys=tuple(snapshot_keys),
        flow_transaction_ids=tuple(t.transaction_id for t in flows),
    )
