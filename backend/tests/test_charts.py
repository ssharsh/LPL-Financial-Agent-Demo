from datetime import date

import pytest

from advisor.charts import (
    accounts_chart,
    allocation_chart,
    chart_from_ledger,
    performance_chart,
    transactions_chart,
)
from advisor.envelope import Chart, build_envelope
from advisor.tools.factory import build_tools, call_tool
from advisor.tools.ledger import RequestLedger, SourceRef

PERF_ARGS = {"start_month": "2024-10", "end_month": "2026-09"}
TXN_ARGS = {"start_date": "2026-01-01", "end_date": "2026-09-30"}


@pytest.fixture
def run(seed_repo, session_for):
    """run(calls) -> (ledger, [results]) for client 1, calling the real tools."""

    def _run(calls):
        ledger = RequestLedger()
        tools = build_tools(session_for(1), seed_repo, ledger)
        return ledger, [call_tool(tools, name, args) for name, args in calls]

    return _run


def test_performance_line(run):
    _, [perf] = run([("get_performance", PERF_ARGS)])
    chart = performance_chart(perf)
    Chart.model_validate(chart)
    assert (chart["type"], chart["x"], chart["y"], chart["series"]) == ("line", "month", "end_value", "")
    assert len(chart["rows"]) == 24
    assert chart["rows"][0]["month"] == "2024-10"
    assert chart["rows"][-1] == {"month": "2026-09", "end_value": perf["end_value"]}


def test_one_month_performance_has_no_chart(run):
    _, [perf] = run([("get_performance", {"start_month": "2026-09", "end_month": "2026-09"})])
    assert performance_chart(perf) is None


def test_holdings_pie_includes_cash_and_exact_values(run):
    _, [holdings] = run([("get_holdings", {})])
    chart = allocation_chart(holdings)
    Chart.model_validate(chart)
    assert chart["type"] == "pie"
    by_class = {r["asset_class"]: r["market_value"] for r in holdings["totals"]["by_asset_class"]}
    rows = {r["asset_class"]: r["market_value"] for r in chart["rows"]}
    assert rows.pop("Cash") == holdings["totals"]["cash"]
    assert rows == by_class


def test_transactions_bar(run):
    _, [txns] = run([("get_transactions", TXN_ARGS)])
    chart = transactions_chart(txns)
    Chart.model_validate(chart)
    assert (chart["type"], chart["x"], chart["y"]) == ("bar", "txn_type", "total_amount")
    assert chart["rows"] == [
        {"txn_type": r["txn_type"], "total_amount": r["total_amount"]} for r in txns["totals"]["by_type"]
    ]


def test_accounts_bar(run):
    _, [accounts] = run([("get_accounts", {})])
    chart = accounts_chart(accounts)
    assert chart["type"] == "bar"
    assert len(chart["rows"]) == 3
    assert chart["rows"][0] == {"account_name": "Individual Brokerage", "total_value": "158751.81"}


def test_priority_prefers_performance(run):
    ledger, _ = run([("get_accounts", {}), ("get_performance", PERF_ARGS)])
    assert chart_from_ledger(ledger)["type"] == "line"


def test_falls_through_when_top_builder_returns_none(run):
    ledger, _ = run([("get_accounts", {}), ("get_performance", {"start_month": "2026-09", "end_month": "2026-09"})])
    assert chart_from_ledger(ledger)["type"] == "bar"


def test_later_empty_call_does_not_hide_earlier_chart(run):
    ledger, [txns] = run([("get_transactions", TXN_ARGS)])
    ledger.record(
        tool="get_transactions", arguments={}, status="success", result={"totals": {"by_type": []}}
    )
    chart = chart_from_ledger(ledger)
    assert chart["type"] == "bar"
    assert len(chart["rows"]) == len(txns["totals"]["by_type"])


def test_malformed_result_gives_no_chart():
    ledger = RequestLedger()
    ledger.record(tool="get_accounts", arguments={}, status="success", result={"tool": "get_accounts"})
    assert chart_from_ledger(ledger) is None


def test_error_calls_ignored():
    ledger = RequestLedger()
    ledger.record(tool="get_holdings", arguments={}, status="error", error="no access")
    assert chart_from_ledger(ledger) is None


def test_envelope_carries_chart(run):
    ledger, _ = run([("get_holdings", {})])
    env = build_envelope("text", ledger, "log_1")
    assert env.chart is not None and env.chart.type == "pie"
    assert env.model_dump(mode="json")["chart"]["rows"][-1]["asset_class"] == "Cash"


def test_envelope_without_chart_tools_has_null_chart():
    ledger = RequestLedger()
    ledger.record(
        tool="get_accounts",
        arguments={},
        status="success",
        result={"tool": "get_accounts"},
        sources=(SourceRef("account", "Accounts", date(2026, 9, 30), ("101",)),),
    )
    assert build_envelope("t", ledger, "log_2").chart is None
