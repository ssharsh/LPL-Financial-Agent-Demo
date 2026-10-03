"""Chart specs derived in code from a turn's tool results.

The model never produces chart data. Every row value is copied unchanged (as the tool's exact string) from a
successful tool result of the same turn, so a chart cannot show a figure the tools did not return.

Spec shape (envelope `chart`): {type, x, y, series, rows}. `series` is "" for single-series charts, else the
row key to group by (long format). Types emitted today: line, bar, pie. The frontend also draws stacked_area
and table, for the Phase-2 explore tool.
"""
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from typing import Any

from advisor.tools.ledger import RequestLedger

ChartDict = dict[str, Any]


def performance_chart(result: dict[str, Any]) -> ChartDict | None:
    """Month-end value over the period. Fewer than two months is not worth a line."""
    rows = result["rows"]
    if len(rows) < 2:
        return None
    return {
        "type": "line",
        "x": "month",
        "y": "end_value",
        "series": "",
        "rows": [{"month": r["month"], "end_value": r["end_value"]} for r in rows],
    }


def allocation_chart(result: dict[str, Any]) -> ChartDict | None:
    """Market value by asset class, plus cash when there is any."""
    totals = result["totals"]
    rows = [{"asset_class": r["asset_class"], "market_value": r["market_value"]} for r in totals["by_asset_class"]]
    cash = totals.get("cash")
    if cash is not None and Decimal(cash) > 0:
        rows.append({"asset_class": "Cash", "market_value": cash})
    if not rows:
        return None
    return {"type": "pie", "x": "asset_class", "y": "market_value", "series": "", "rows": rows}


def transactions_chart(result: dict[str, Any]) -> ChartDict | None:
    """Total amount by transaction type."""
    by_type = result["totals"]["by_type"]
    if not by_type:
        return None
    return {
        "type": "bar",
        "x": "txn_type",
        "y": "total_amount",
        "series": "",
        "rows": [{"txn_type": r["txn_type"], "total_amount": r["total_amount"]} for r in by_type],
    }


def accounts_chart(result: dict[str, Any]) -> ChartDict | None:
    """Latest total value per account."""
    rows = result["rows"]
    if not rows:
        return None
    return {
        "type": "bar",
        "x": "account_name",
        "y": "total_value",
        "series": "",
        "rows": [
            {"account_name": r.get("account_name") or str(r["account_id"]), "total_value": r["total_value"]}
            for r in rows
        ],
    }


# Highest priority first: a turn that looked at performance is best shown as a line, and so on.
_BUILDERS: tuple[tuple[str, Callable[[dict[str, Any]], ChartDict | None]], ...] = (
    ("get_performance", performance_chart),
    ("get_holdings", allocation_chart),
    ("get_transactions", transactions_chart),
    ("get_accounts", accounts_chart),
)


def safe_chart(builder: Callable[[dict[str, Any]], ChartDict | None], result: Any) -> ChartDict | None:
    """Run a builder; a missing key or odd value means no chart, never a failed answer."""
    try:
        return builder(result)
    except (KeyError, TypeError, ValueError, InvalidOperation, AttributeError):
        return None


def chart_from_ledger(ledger: RequestLedger) -> ChartDict | None:
    """Chart the highest-priority tool called successfully this turn, using its latest call that yields a
    chart (e.g. a later empty withdrawals query does not hide an earlier deposits chart). Falls through to
    lower-priority tools when none of a tool's calls yields a chart."""
    calls = [c for c in ledger.calls() if c.status == "success" and c.result is not None]
    for tool, builder in _BUILDERS:
        for call in reversed(calls):
            if call.tool == tool:
                chart = safe_chart(builder, call.result)
                if chart is not None:
                    return chart
    return None
