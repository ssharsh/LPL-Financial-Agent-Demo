"""get_performance through the tool: hand fixtures F1-F6 and seed checks against an independent Fraction-based
Modified Dietz computed here (not with advisor.calc.performance)."""

import calendar
from datetime import date
from decimal import ROUND_HALF_EVEN, Decimal
from fractions import Fraction

import pytest

from advisor.calc.performance import RETURN_LABEL
from advisor.data.memory_repo import MemoryRepository
from advisor.errors import AccountAccessError, DataUnavailableError, ToolArgumentError
from advisor.identity import resolve_identity
from advisor.tools.factory import build_tools
from advisor.tools.ledger import RequestLedger
from fixtures import (
    ACCT_X,
    FIXTURE_CLIENT_ID,
    f1_dataset,
    f1_f2_dataset,
    f2_dataset,
    f3_dataset,
    f4_dataset,
    f5_dataset,
    f6_dataset,
)

RESULT_KEYS = [
    "tool",
    "period",
    "scope",
    "start_value",
    "start_value_date",
    "end_value",
    "end_value_date",
    "net_flows",
    "investment_gain",
    "time_weighted_return_pct",
    "return_label",
    "return_unavailable_reason",
    "rows",
    "rounding",
    "calculation_method",
    "sources",
]


def perf_tool(repo, client_id):
    session = resolve_identity(repo, mode="dev", credential=str(client_id))
    tools = {t.tool_name: t for t in build_tools(session, repo, RequestLedger())}
    return tools["get_performance"]


def fixture_perf(dataset):
    return perf_tool(MemoryRepository(dataset), FIXTURE_CLIENT_ID)


def assert_no_simple_change(result):
    for key in result:
        assert "simple" not in key and "percent_change" not in key and "pct_change" not in key


# -- hand fixtures -------------------------------------------------------------------------------------------


def test_f1_through_tool():
    result = fixture_perf(f1_dataset())(start_month="2025-04", end_month="2025-04")
    assert list(result) == RESULT_KEYS
    (row,) = result["rows"]
    assert row["monthly_return_pct"] == "4.70"
    assert row["weighted_flow"] == "633.33"
    assert row["denominator"] == "10633.33"
    assert result["time_weighted_return_pct"] == "4.70"
    assert result["investment_gain"] == "500.00"
    assert result["return_label"] == RETURN_LABEL == "time-weighted return (monthly Modified Dietz, linked)"


def test_f2_through_tool():
    result = fixture_perf(f2_dataset())(start_month="2025-05", end_month="2025-05")
    (row,) = result["rows"]
    assert row["monthly_return_pct"] == "2.76"
    assert row["weighted_flow"] == "-645.16"
    assert row["denominator"] == "10854.84"


def test_f1_f2_linked_through_tool_has_no_simple_percent_change():
    result = fixture_perf(f1_f2_dataset())(start_month="2025-04", end_month="2025-05")
    assert result["time_weighted_return_pct"] == "7.60"
    assert result["start_value"] == "10000.00"
    assert result["end_value"] == "9800.00"
    assert result["net_flows"] == "-1000.00"
    assert result["investment_gain"] == "800.00"
    assert result["scope"] == {"account_ids": [ACCT_X], "level": "portfolio (all accounts combined)"}
    # a simple percent change would be -2.00%; it must not appear anywhere in the output
    assert_no_simple_change(result)
    assert "-2.00" not in str(result)
    snap_src, txn_src = result["sources"]
    assert snap_src["type"] == "portfolio_snapshot" and snap_src["as_of"] == "2025-05-31"
    assert snap_src["record_ids"] == ["901@2025-03-31", "901@2025-04-30", "901@2025-05-31"]
    assert txn_src["type"] == "transaction" and txn_src["record_ids"] == ["1", "2"]


def test_f6_through_tool():
    result = fixture_perf(f6_dataset())(start_month="2025-06", end_month="2025-06")
    (row,) = result["rows"]
    assert row["monthly_return_pct"] == "2.69"
    assert row["weighted_flow"] == "2333.33"


def test_f5_through_tool():
    result = fixture_perf(f5_dataset())(start_month="2025-04", end_month="2025-04")
    assert result["time_weighted_return_pct"] == "8.18"


def test_f3_through_tool():
    result = fixture_perf(f3_dataset())(start_month="2025-07", end_month="2025-08")
    july, august = result["rows"]
    assert july["monthly_return_pct"] is None and "2025-07" in july["reason"]
    assert august["monthly_return_pct"] == "2.00" and august["reason"] is None
    assert result["time_weighted_return_pct"] is None
    assert "2025-07" in result["return_unavailable_reason"]
    assert result["start_value"] == "0.00"
    assert result["end_value"] == "5100.00"
    assert result["net_flows"] == "5000.00"
    assert result["investment_gain"] == "100.00"


def test_f4_through_tool():
    tool = fixture_perf(f4_dataset())
    with pytest.raises(DataUnavailableError, match="2025-04"):
        tool(start_month="2025-03", end_month="2025-04")
    with pytest.raises(DataUnavailableError, match="latest valid end month is 2025-08"):
        tool(start_month="2025-08", end_month="2025-09")
    with pytest.raises(DataUnavailableError, match="2025-06-30"):
        tool(start_month="2025-04", end_month="2025-08")
    with pytest.raises(ToolArgumentError):
        tool(start_month="2025-05", end_month="2025-04")


# -- seed ----------------------------------------------------------------------------------------------------


@pytest.mark.parametrize("client_id,net_flows", [(1, "36000.00"), (2, "-800.00"), (3, "21000.00")])
def test_seed_net_flows_full_window(seed_repo, client_id, net_flows):
    result = perf_tool(seed_repo, client_id)(start_month="2024-10", end_month="2026-09")
    assert result["net_flows"] == net_flows
    assert result["start_value_date"] == "2024-09-30"
    assert result["end_value_date"] == "2026-09-30"
    assert len(result["rows"]) == 24
    assert result["return_label"] == RETURN_LABEL
    assert_no_simple_change(result)


def test_seed_client2_september_2026(seed_repo):
    result = perf_tool(seed_repo, 2)(start_month="2026-09", end_month="2026-09")
    assert result["net_flows"] == "-7700.00"
    assert result["return_label"] == "time-weighted return (monthly Modified Dietz, linked)"


def test_seed_start_before_opening_snapshot(seed_repo):
    with pytest.raises(DataUnavailableError, match="2024-10"):
        perf_tool(seed_repo, 1)(start_month="2024-09", end_month="2026-09")


def test_seed_end_after_data_as_of(seed_repo):
    with pytest.raises(DataUnavailableError, match="2026-09-30"):
        perf_tool(seed_repo, 1)(start_month="2026-09", end_month="2026-10")


def _month_end(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


def independent_twr(repo, session, account_ids, start, end) -> Fraction:
    """Modified Dietz with exact Fractions straight from repo rows."""
    values = {
        (s.account_id, s.snapshot_date): Fraction(s.total_value)
        for s in repo.list_snapshots(session, account_ids)
    }
    txns = repo.list_transactions(session, account_ids)
    growth = Fraction(1)
    year, month = start
    while (year, month) <= end:
        prev = (year - 1, 12) if month == 1 else (year, month - 1)
        bmv = sum(values[(a, _month_end(*prev))] for a in account_ids)
        emv = sum(values[(a, _month_end(year, month))] for a in account_ids)
        days = calendar.monthrange(year, month)[1]
        flow = Fraction(0)
        weighted = Fraction(0)
        for t in txns:
            if (t.txn_date.year, t.txn_date.month) != (year, month):
                continue
            if t.txn_type == "deposit":
                f = Fraction(t.amount)
            elif t.txn_type == "withdrawal":
                f = -Fraction(t.amount)
            else:
                continue
            flow += f
            weighted += Fraction(days - t.txn_date.day, days) * f
        growth *= 1 + (emv - bmv - flow) / (bmv + weighted)
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return growth - 1


def as_pct_string(fraction: Fraction) -> str:
    pct = Decimal(fraction.numerator * 100) / Decimal(fraction.denominator)
    return str(pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN))


@pytest.mark.parametrize("client_id", [1, 2, 3])
def test_seed_twr_matches_independent_fraction_computation(seed_repo, session_for, client_id):
    session = session_for(client_id)
    account_ids = [a.account_id for a in seed_repo.list_accounts(session)]
    result = perf_tool(seed_repo, client_id)(start_month="2024-10", end_month="2026-09")
    expected = independent_twr(seed_repo, session, account_ids, (2024, 10), (2026, 9))
    assert result["time_weighted_return_pct"] == as_pct_string(expected)
    assert Decimal(result["investment_gain"]) == (
        Decimal(result["end_value"]) - Decimal(result["start_value"]) - Decimal(result["net_flows"])
    )


def test_seed_account_scope(seed_repo, session_for):
    tool = perf_tool(seed_repo, 2)
    result = tool(start_month="2026-09", end_month="2026-09", account_id=105)
    assert result["scope"] == {"account_ids": [105], "level": "account 105"}
    assert result["net_flows"] == "-7700.00"
    expected = independent_twr(seed_repo, session_for(2), [105], (2026, 9), (2026, 9))
    assert result["time_weighted_return_pct"] == as_pct_string(expected)
    with pytest.raises(AccountAccessError, match="Account 101 is not one of this client's accounts."):
        tool(start_month="2026-09", end_month="2026-09", account_id=101)
