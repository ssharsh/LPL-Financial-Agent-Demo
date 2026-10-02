import json
from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from advisor.calc.cash_model import cash_effect
from advisor.data.memory_repo import MemoryRepository
from advisor.errors import AccountAccessError, DataConsistencyError, DataUnavailableError, ToolArgumentError
from advisor.identity import resolve_identity
from advisor.tools.common import canonical_json, money, price, quantity, sha256_hex
from advisor.tools.factory import TOOL_NAMES, build_tools, call_tool
from advisor.tools.ledger import RequestLedger, SourceRef
from fixtures import FIXTURE_CLIENT_ID, flow_dataset

FORBIDDEN_PARAMS = {"client_id", "customer_id", "advisor_id", "owner", "firm_id"}
EXPECTED_PROPERTIES = {
    "get_accounts": set(),
    "get_holdings": {"as_of_month", "account_id"},
    "get_transactions": {"start_date", "end_date", "txn_type", "account_id"},
    "get_performance": {"start_month", "end_month", "account_id"},
}
ACCOUNT_TOOL_CALLS = [
    ("get_holdings", {}),
    ("get_transactions", {"start_date": "2026-09-01", "end_date": "2026-09-30"}),
    ("get_performance", {"start_month": "2026-09", "end_month": "2026-09"}),
]


def make_tools(repo, client_id):
    session = resolve_identity(repo, mode="dev", credential=str(client_id))
    ledger = RequestLedger()
    tools = build_tools(session, repo, ledger)
    return {t.tool_name: t for t in tools}, tools, ledger


@pytest.fixture
def client1(seed_repo):
    return make_tools(seed_repo, 1)


def walk(value):
    yield value
    if isinstance(value, dict):
        for v in value.values():
            yield from walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


# -- schemas -------------------------------------------------------------------------------------------------


def test_tool_names_and_order(client1):
    _, tools, _ = client1
    assert tuple(t.tool_name for t in tools) == TOOL_NAMES


def test_tool_input_schemas_have_exact_properties_and_no_identity(client1):
    by_name, _, _ = client1
    for name, expected in EXPECTED_PROPERTIES.items():
        schema = by_name[name].tool_spec["inputSchema"]["json"]
        props = set(schema.get("properties", {}))
        assert props == expected, name
        assert not props & FORBIDDEN_PARAMS, name
    txn_schema = by_name["get_transactions"].tool_spec["inputSchema"]["json"]
    assert txn_schema["properties"]["txn_type"]["enum"] == [
        "buy",
        "sell",
        "dividend",
        "deposit",
        "withdrawal",
        "fee",
    ]
    assert set(txn_schema["required"]) == {"start_date", "end_date"}
    perf_schema = by_name["get_performance"].tool_spec["inputSchema"]["json"]
    assert set(perf_schema["required"]) == {"start_month", "end_month"}


# -- ownership -----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name,base_args", ACCOUNT_TOOL_CALLS)
def test_foreign_and_nonexistent_accounts_get_identical_error(client1, name, base_args):
    by_name, tools, _ = client1
    messages = []
    for account_id in (104, 999):
        with pytest.raises(AccountAccessError) as direct:
            by_name[name](**base_args, account_id=account_id)
        with pytest.raises(AccountAccessError) as via_cli:
            call_tool(tools, name, {**base_args, "account_id": account_id})
        assert str(direct.value) == str(via_cli.value)
        messages.append(str(direct.value).replace(str(account_id), "<id>"))
    assert messages[0] == messages[1] == "Account <id> is not one of this client's accounts."


def test_call_tool_rejects_identity_argument(client1):
    _, tools, ledger = client1
    with pytest.raises(ToolArgumentError, match="client_id"):
        call_tool(tools, "get_accounts", {"client_id": 2})
    with pytest.raises(ToolArgumentError, match="client_id"):
        call_tool(tools, "get_holdings", {"client_id": 2})
    assert ledger.calls() == ()  # rejected before reaching tool code


def test_call_tool_rejects_unknown_tool_and_missing_args(client1):
    _, tools, _ = client1
    with pytest.raises(ToolArgumentError, match="get_accounts, get_holdings, get_transactions, get_performance"):
        call_tool(tools, "get_documents", {})
    with pytest.raises(ToolArgumentError, match="end_month"):
        call_tool(tools, "get_performance", {"start_month": "2026-09"})
    with pytest.raises(ToolArgumentError, match="JSON object"):
        call_tool(tools, "get_accounts", [1])


@pytest.mark.parametrize(
    "name,args",
    [
        ("get_holdings", {"as_of_month": "2026-9"}),
        ("get_holdings", {"as_of_month": "2026-13"}),
        ("get_holdings", {"account_id": "101"}),
        ("get_transactions", {"start_date": "2026/09/01", "end_date": "2026-09-30"}),
        ("get_transactions", {"start_date": "2026-02-30", "end_date": "2026-09-30"}),
        ("get_transactions", {"start_date": "2026-09-30", "end_date": "2026-09-01"}),
        ("get_transactions", {"start_date": "2026-09-01", "end_date": "2026-09-30", "txn_type": "rebalance"}),
        ("get_performance", {"start_month": "Sept 2026", "end_month": "2026-09"}),
        ("get_performance", {"start_month": "2026-09", "end_month": "2026-08"}),
    ],
)
def test_invalid_arguments_raise_tool_argument_error_and_are_logged(client1, name, args):
    _, tools, ledger = client1
    with pytest.raises(ToolArgumentError):
        call_tool(tools, name, args)
    (call,) = ledger.calls()
    assert call.status == "error"
    assert call.tool == name
    assert call.error
    assert call.result is None and call.result_sha256 is None


# -- ledger and result shape ---------------------------------------------------------------------------------


def test_every_call_is_in_the_ledger(client1):
    by_name, _, ledger = client1
    first = by_name["get_accounts"]()
    with pytest.raises(AccountAccessError):
        by_name["get_holdings"](account_id=104)
    second = by_name["get_performance"](start_month="2026-09", end_month="2026-09")

    calls = ledger.calls()
    assert [c.sequence for c in calls] == [1, 2, 3]
    assert [c.tool for c in calls] == ["get_accounts", "get_holdings", "get_performance"]
    assert [c.status for c in calls] == ["success", "error", "success"]

    ok1, err, ok2 = calls
    assert ok1.arguments == {}
    assert ok1.result == first and ok1.result_sha256 == sha256_hex(first)
    assert ok2.arguments == {"start_month": "2026-09", "end_month": "2026-09", "account_id": None}
    assert ok2.result == second and ok2.result_sha256 == sha256_hex(second)
    for ok in (ok1, ok2):
        assert ok.sources and all(isinstance(s, SourceRef) for s in ok.sources)
        assert ok.calculation_method and ok.result["calculation_method"] == ok.calculation_method
        assert ok.result["sources"] == [s.to_json() for s in ok.sources]
        assert ok.called_at.tzinfo is not None
    assert err.arguments == {"as_of_month": None, "account_id": 104}
    assert "Account 104" in err.error
    assert err.sources == () and err.result is None


def test_ledger_sources_are_successful_calls_only_and_deduplicated(client1):
    by_name, _, ledger = client1
    by_name["get_accounts"]()
    by_name["get_accounts"]()
    with pytest.raises(AccountAccessError):
        by_name["get_transactions"](start_date="2026-09-01", end_date="2026-09-30", account_id=104)
    sources = ledger.sources()
    assert [(s.type, s.description) for s in sources] == [
        (s.type, s.description) for s in ledger.calls()[0].sources
    ]
    assert all(s.type != "transaction" for s in sources)


def test_results_are_json_safe_and_never_status_plus_content(client1):
    by_name, _, _ = client1
    results = [
        by_name["get_accounts"](),
        by_name["get_holdings"](),
        by_name["get_holdings"](as_of_month="2025-06", account_id=101),
        by_name["get_transactions"](start_date="2024-09-01", end_date="2026-09-30"),
        by_name["get_performance"](start_month="2024-10", end_month="2026-09"),
    ]
    for result in results:
        json.dumps(result)  # no default= : a Decimal would raise
        canonical_json(result)
        assert not ("status" in result and "content" in result)
        for value in walk(result):
            assert not isinstance(value, (Decimal, float, date))


# -- get_accounts --------------------------------------------------------------------------------------------


def test_get_accounts_totals_equal_latest_snapshots(client1, seed_repo, session_for):
    by_name, _, _ = client1
    result = by_name["get_accounts"]()
    snaps = seed_repo.list_snapshots(session_for(1), start_date=date(2026, 9, 30))
    assert [r["account_id"] for r in result["rows"]] == [101, 102, 103]
    assert result["data_as_of"] == "2026-09-30"
    assert result["totals"]["account_count"] == 3
    assert result["totals"]["total_value"] == money(sum(s.total_value for s in snaps))
    assert result["rows"][0]["total_value"] == "158751.81"  # golden seed value (test_seed)
    cash = sum(a.cash_balance for a in seed_repo.list_accounts(session_for(1)))
    assert result["totals"]["cash_balance"] == money(cash)


# -- get_holdings --------------------------------------------------------------------------------------------


def test_get_holdings_default_is_current_records_at_data_as_of(client1):
    by_name, _, _ = client1
    result = by_name["get_holdings"]()
    assert result["as_of_date"] == "2026-09-30"
    assert result["position_basis"] == "current holdings records"
    assert all(r["avg_cost_basis"] is not None and r["first_purchased"] is not None for r in result["rows"])
    assert all(r["price_date"] == "2026-09-30" for r in result["rows"])


def test_get_holdings_derived_2026_09_matches_current(client1):
    by_name, _, _ = client1
    current = by_name["get_holdings"]()
    derived = by_name["get_holdings"](as_of_month="2026-09")
    assert derived["position_basis"] == "derived from buy and sell transactions through 2026-09-30"

    def key(rows):
        return [(r["account_id"], r["security_id"], r["quantity"], r["market_value"]) for r in rows]

    assert key(derived["rows"]) == key(current["rows"])
    assert derived["cash"] == current["cash"]
    assert derived["totals"]["total_value"] == current["totals"]["total_value"]
    assert all(r["avg_cost_basis"] is None and r["first_purchased"] is None for r in derived["rows"])


@pytest.mark.parametrize("client_id", [1, 2, 3])
def test_get_holdings_2025_06_equals_snapshots(seed_repo, session_for, client_id):
    by_name, _, _ = make_tools(seed_repo, client_id)
    result = by_name["get_holdings"](as_of_month="2025-06")
    snaps = seed_repo.list_snapshots(session_for(client_id), start_date=date(2025, 6, 30), end_date=date(2025, 6, 30))
    assert result["totals"]["total_value"] == money(sum(s.total_value for s in snaps))
    for row in result["totals"]["by_account"]:
        (snap,) = [s for s in snaps if s.account_id == row["account_id"]]
        assert row["total_value"] == money(snap.total_value)


def test_get_holdings_totals_are_sums_of_rows(client1):
    by_name, _, _ = client1
    result = by_name["get_holdings"]()
    totals = result["totals"]
    rows_value = sum(Decimal(r["market_value"]) for r in result["rows"])
    cash_value = sum(Decimal(c["cash"]) for c in result["cash"])
    assert money(rows_value) == totals["securities_value"]
    assert money(cash_value) == totals["cash"]
    assert money(rows_value + cash_value) == totals["total_value"]
    assert money(sum(Decimal(a["total_value"]) for a in totals["by_account"])) == totals["total_value"]
    assert money(sum(Decimal(s["market_value"]) for s in totals["by_security"])) == totals["securities_value"]
    assert money(sum(Decimal(c["market_value"]) for c in totals["by_asset_class"])) == totals["securities_value"]
    for r in result["rows"]:
        assert Decimal(r["market_value"]) == (Decimal(r["quantity"]) * Decimal(r["close_price"])).quantize(
            Decimal("0.01")
        )


def test_get_holdings_beyond_data_as_of(client1):
    by_name, _, _ = client1
    with pytest.raises(DataUnavailableError, match="2026-09-30"):
        by_name["get_holdings"](as_of_month="2026-10")


def test_get_holdings_before_first_snapshot(client1):
    by_name, _, _ = client1
    with pytest.raises(DataUnavailableError, match="2024-09 through 2026-09"):
        by_name["get_holdings"](as_of_month="2024-08")


@pytest.mark.parametrize("as_of_month,missing_day", [("2025-06", date(2025, 6, 30)), (None, date(2026, 9, 30))])
def test_get_holdings_missing_price_names_ticker_and_date(seed_dataset, as_of_month, missing_day):
    dataset = replace(
        seed_dataset,
        security_prices=tuple(
            p for p in seed_dataset.security_prices if not (p.security_id == 201 and p.price_date == missing_day)
        ),
    )
    by_name, _, ledger = make_tools(MemoryRepository(dataset), 1)
    with pytest.raises(DataUnavailableError) as exc:
        by_name["get_holdings"](as_of_month=as_of_month)
    assert "QXLC" in str(exc.value) and missing_day.isoformat() in str(exc.value)
    assert ledger.calls()[-1].status == "error"


# -- get_transactions ----------------------------------------------------------------------------------------


def test_get_transactions_beyond_data_as_of(client1):
    by_name, _, _ = client1
    with pytest.raises(DataUnavailableError, match="2026-09-30"):
        by_name["get_transactions"](start_date="2026-09-01", end_date="2026-10-31")


def test_get_transactions_totals_match_rows(seed_repo, session_for):
    by_name, _, _ = make_tools(seed_repo, 2)
    result = by_name["get_transactions"](start_date="2026-09-01", end_date="2026-09-30")
    rows = result["rows"]
    expected = seed_repo.list_transactions(session_for(2), start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))
    assert [r["transaction_id"] for r in rows] == [
        t.transaction_id for t in sorted(expected, key=lambda t: (t.txn_date, t.transaction_id))
    ]
    assert result["totals"]["count"] == len(rows)
    counts = {b["txn_type"]: b["count"] for b in result["totals"]["by_type"]}
    for txn_type, count in counts.items():
        assert count == sum(1 for r in rows if r["txn_type"] == txn_type)
    assert sum(counts.values()) == len(rows)
    for b in result["totals"]["by_type"]:
        assert b["total_amount"] == money(sum(Decimal(r["amount"]) for r in rows if r["txn_type"] == b["txn_type"]))
    assert result["totals"]["net_cash_effect"] == money(sum(cash_effect(t) for t in expected))
    assert result["totals"]["net_cash_effect"] == money(sum(Decimal(r["cash_effect"]) for r in rows))
    withdrawals = [r for r in rows if r["txn_type"] == "withdrawal"]
    assert [(w["txn_date"], w["amount"], w["cash_effect"], w["account_id"]) for w in withdrawals] == [
        ("2026-09-15", "8000.00", "-8000.00", 105)
    ]


def test_get_transactions_type_and_account_filters(client1):
    by_name, _, _ = client1
    result = by_name["get_transactions"](
        start_date="2024-09-01", end_date="2026-09-30", txn_type="sell", account_id=101
    )
    assert [(r["txn_date"], r["ticker"], r["quantity"], r["price"]) for r in result["rows"]] == [
        ("2025-12-10", "QXLC", "59", "107.89")
    ]
    assert result["rows"][0]["amount"] == "6365.51"
    assert result["rows"][0]["cash_effect"] == "6365.51"


# -- D4 guard ------------------------------------------------------------------------------------------------


def test_d4_guard_transaction_after_latest_snapshot():
    dataset = flow_dataset(
        (901,),
        [(901, "2025-03-31", "10000.00"), (901, "2025-04-30", "11500.00")],
        [(901, "deposit", "2025-04-11", "1000.00"), (901, "deposit", "2025-05-02", "50.00")],
    )
    by_name, _, ledger = make_tools(MemoryRepository(dataset), FIXTURE_CLIENT_ID)
    for name, args in [
        ("get_accounts", {}),
        ("get_holdings", {}),
        ("get_transactions", {"start_date": "2025-04-01", "end_date": "2025-04-30"}),
        ("get_performance", {"start_month": "2025-04", "end_month": "2025-04"}),
    ]:
        with pytest.raises(DataConsistencyError, match="2025-04-30"):
            by_name[name](**args)
    assert [c.status for c in ledger.calls()] == ["error"] * 4


# -- formatters ----------------------------------------------------------------------------------------------


def test_formatters():
    assert canonical_json({"b": "1.00", "a": [1, 2]}) == '{"a":[1,2],"b":"1.00"}'
    assert money(Decimal("-0.001")) == "0.00"
    assert money(Decimal("12.345")) == "12.34"  # half-even
    assert quantity(Decimal("100.0000")) == "100"
    assert quantity(Decimal("12.5000")) == "12.5"
    assert price(Decimal("104.5")) == "104.50"
    assert price(Decimal("104.5900")) == "104.59"
    assert price(Decimal("20.1234")) == "20.1234"
    with pytest.raises(ValueError):
        price(Decimal("1.23456"))
