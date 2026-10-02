import dataclasses
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal

import pytest

from advisor.calc.months import is_month_end, iter_months, month_end
from advisor.data.models import (
    ACCOUNT_TYPES,
    EXPOSURE_TYPES,
    FINANCIAL_LITERACY_LEVELS,
    RISK_TOLERANCES,
    SECURITY_TYPES,
    TXN_TYPES,
)
from advisor.data.seed import PRICE_SPECS, generate_dataset, summarize

D = Decimal

# golden: changes to seed.py must be deliberate (captured after every invariant test below passed)
GOLDEN_FINGERPRINT = "aa71d3d6d682264c8d8d32bcd939891215941f1bef6c1ad00bf22c871719df50"
GOLDEN_BUY_COUNT = 399
GOLDEN_QXLC_CLOSE_2026_09_30 = D("107.05")
GOLDEN_ACCOUNT_105_SELL_QTY_2026_09_14 = D("77")
GOLDEN_ACCOUNT_101_TOTAL_VALUE_2026_09_30 = D("158751.81")


def fingerprint(dataset) -> str:
    """SHA-256 of the canonical JSON of the whole dataset."""
    text = json.dumps(
        dataclasses.asdict(dataset), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def ds():
    return generate_dataset()


def _closes(ds):
    return {(p.security_id, p.price_date): p.close_price for p in ds.security_prices}


def _fits(value: Decimal, precision: int, scale: int) -> bool:
    if value != value.quantize(D(1).scaleb(-scale)):
        return False
    return abs(value) < D(10) ** (precision - scale)


# ---------------------------------------------------------------------------------------------------------------
# Determinism and counts
# ---------------------------------------------------------------------------------------------------------------


def test_generate_dataset_is_deterministic(ds):
    again = generate_dataset()
    assert again == ds
    assert fingerprint(again) == fingerprint(ds)


def test_exact_rng_independent_counts(ds):
    assert len(ds.advisors) == 2
    assert len(ds.clients) == 3
    assert len(ds.accounts) == 7
    assert len(ds.asset_classes) == 5
    assert len(ds.securities) == 8
    assert len(ds.security_prices) == 6080
    assert len(ds.portfolio_snapshots) == 175
    assert len(ds.holdings) == 29
    assert len(ds.security_exposures) == 1665
    counts = Counter(t.txn_type for t in ds.transactions)
    assert counts["deposit"] == 103
    assert counts["withdrawal"] == 2
    assert counts["sell"] == 3
    assert counts["fee"] == 56
    assert counts["dividend"] == 373


def test_people_and_ownership(ds):
    advisor_1 = next(a for a in ds.advisors if a.advisor_id == 1)
    assert advisor_1.first_name == "Sarah"
    assert {c.client_id: c.advisor_id for c in ds.clients} == {1: 1, 2: 1, 3: 2}
    owned = defaultdict(list)
    for account in ds.accounts:
        owned[account.client_id].append(account.account_id)
    assert dict(owned) == {1: [101, 102, 103], 2: [104, 105], 3: [106, 107]}


def test_ids_are_sequential(ds):
    assert [t.transaction_id for t in ds.transactions] == list(range(1, len(ds.transactions) + 1))
    assert [h.holding_id for h in ds.holdings] == list(range(1, 30))
    assert [h.holding_id for h in sorted(ds.holdings, key=lambda h: (h.account_id, h.security_id))] == list(
        range(1, 30)
    )
    assert [e.exposure_id for e in ds.security_exposures] == list(range(1, 1666))


def test_dates_and_summary(ds):
    summary = summarize(ds)
    assert summary.txn_first_date == date(2024, 9, 3)
    assert summary.txn_last_date == date(2026, 9, 25)
    assert summary.price_first_date == date(2024, 9, 1)
    assert summary.price_last_date == date(2026, 9, 30)
    assert summary.snapshot_last_date == date(2026, 9, 30)
    assert summary.snapshot_month_count == 25
    assert dict(summary.txn_counts_by_type)["deposit"] == 103
    assert [t for t, _ in summary.txn_counts_by_type] == list(TXN_TYPES)
    assert [len(c.accounts) for c in summary.clients] == [3, 2, 2]


# ---------------------------------------------------------------------------------------------------------------
# Enums and column fit
# ---------------------------------------------------------------------------------------------------------------


def test_enum_values_are_valid(ds):
    assert all(a.account_type in ACCOUNT_TYPES for a in ds.accounts)
    assert all(s.security_type in SECURITY_TYPES for s in ds.securities)
    assert all(c.risk_tolerance in RISK_TOLERANCES for c in ds.clients)
    assert all(c.financial_literacy in FINANCIAL_LITERACY_LEVELS for c in ds.clients)
    assert all(t.txn_type in TXN_TYPES for t in ds.transactions)
    assert all(e.exposure_type in EXPOSURE_TYPES for e in ds.security_exposures)
    assert {e.exposure_type for e in ds.security_exposures} == {"sector", "industry"}
    assert all(1 <= s.risk_rating <= 5 for s in ds.securities)


def test_numeric_columns_fit(ds):
    for a in ds.accounts:
        assert _fits(a.cash_balance, 14, 2)
    for t in ds.transactions:
        assert _fits(t.amount, 14, 2)
        if t.quantity is not None:
            assert _fits(t.quantity, 14, 4)
        if t.price is not None:
            assert _fits(t.price, 12, 4)
    for s in ds.portfolio_snapshots:
        assert _fits(s.total_value, 14, 2)
    for h in ds.holdings:
        assert _fits(h.quantity, 14, 4)
        assert _fits(h.avg_cost_basis, 12, 4)
    for p in ds.security_prices:
        assert _fits(p.close_price, 12, 4)
    for e in ds.security_exposures:
        assert _fits(e.weight_pct, 5, 2)
    for s in ds.securities:
        assert _fits(s.expense_ratio, 5, 4)


def test_varchar_columns_fit(ds):
    for a in ds.advisors:
        assert len(a.first_name) <= 50 and len(a.last_name) <= 50 and len(a.email) <= 120
        assert a.email.endswith("@example.com")
    for c in ds.clients:
        assert len(c.first_name) <= 50 and len(c.last_name) <= 50 and len(c.email) <= 120
        assert c.email.endswith("@example.com")
    for a in ds.accounts:
        assert len(a.account_name) <= 100 and len(a.objective) <= 100
    for c in ds.asset_classes:
        assert len(c.name) <= 50 and len(c.color_hex) <= 7
    for s in ds.securities:
        assert len(s.ticker) <= 10 and len(s.name) <= 150
        assert s.sector is None or len(s.sector) <= 50
        assert len(s.region) <= 50
    for e in ds.security_exposures:
        assert len(e.label) <= 100
    emails = [a.email for a in ds.advisors] + [c.email for c in ds.clients]
    assert len(set(emails)) == len(emails)
    assert len({s.ticker for s in ds.securities}) == 8


# ---------------------------------------------------------------------------------------------------------------
# Snapshots and prices
# ---------------------------------------------------------------------------------------------------------------


def test_snapshots_are_month_ends_25_per_account(ds):
    expected = [month_end(y, m) for y, m in iter_months((2024, 9), (2026, 9))]
    by_account = defaultdict(list)
    for s in ds.portfolio_snapshots:
        assert is_month_end(s.snapshot_date)
        by_account[s.account_id].append(s.snapshot_date)
    assert sorted(by_account) == [101, 102, 103, 104, 105, 106, 107]
    for dates in by_account.values():
        assert dates == expected
    assert all(s.total_contributions is None for s in ds.portfolio_snapshots)


def test_prices_cover_every_day_and_start_prices(ds):
    closes = _closes(ds)
    assert len(closes) == 6080
    for sid, spec in PRICE_SPECS.items():
        assert closes[(sid, date(2024, 9, 1))] == spec.start
    for t in ds.transactions:
        if t.security_id is not None:
            assert (t.security_id, t.txn_date) in closes
    for s in ds.portfolio_snapshots:
        for sid in PRICE_SPECS:
            assert (sid, s.snapshot_date) in closes
    assert all(p.close_price > 0 for p in ds.security_prices)


# ---------------------------------------------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------------------------------------------


def test_trades_use_the_close_and_exact_amounts(ds):
    closes = _closes(ds)
    for t in ds.transactions:
        if t.txn_type in ("buy", "sell"):
            assert t.security_id is not None
            assert t.price == closes[(t.security_id, t.txn_date)]
            assert t.quantity == t.quantity.to_integral_value() and t.quantity > 0
            assert t.amount == t.quantity * t.price


def test_null_patterns(ds):
    for t in ds.transactions:
        if t.txn_type in ("deposit", "withdrawal", "fee"):
            assert (t.security_id, t.quantity, t.price) == (None, None, None)
        elif t.txn_type == "dividend":
            assert t.security_id is not None and t.quantity is None and t.price is None
    assert all(s.dividend_yield is None for s in ds.securities)
    assert all(s.expense_ratio < 1 for s in ds.securities)


def test_all_amounts_positive(ds):
    assert all(t.amount > 0 for t in ds.transactions)


def test_running_cash_never_negative(ds):
    signs = {"deposit": 1, "sell": 1, "dividend": 1, "withdrawal": -1, "buy": -1, "fee": -1}
    cash = defaultdict(lambda: D("0.00"))
    for t in sorted(ds.transactions, key=lambda t: t.transaction_id):
        cash[t.account_id] += signs[t.txn_type] * t.amount
        assert cash[t.account_id] >= 0, t


def test_same_day_order(ds):
    order = {"deposit": 0, "sell": 1, "buy": 2, "dividend": 3, "fee": 4, "withdrawal": 5}
    keys = [(t.txn_date, t.account_id, order[t.txn_type], t.security_id or 0) for t in ds.transactions]
    assert keys == sorted(keys)


def test_only_september_2026_withdrawal(ds):
    sep = [t for t in ds.transactions if t.txn_type == "withdrawal" and (t.txn_date.year, t.txn_date.month) == (2026, 9)]
    assert len(sep) == 1
    assert (sep[0].account_id, sep[0].txn_date, sep[0].amount) == (105, date(2026, 9, 15), D("8000.00"))


def test_events(ds):
    sells = [t for t in ds.transactions if t.txn_type == "sell"]
    assert [(t.account_id, t.txn_date, t.security_id) for t in sells] == [
        (106, date(2025, 6, 10), 202),
        (101, date(2025, 12, 10), 201),
        (105, date(2026, 9, 14), 201),
    ]
    assert sells[0].amount >= D("15000") and sells[2].amount >= D("8000")
    rebalance_buys = [
        t for t in ds.transactions if t.txn_type == "buy" and (t.account_id, t.txn_date) == (101, date(2025, 12, 10))
    ]
    assert [t.security_id for t in rebalance_buys] == [205]
    assert rebalance_buys[0].amount <= sells[1].amount


def test_fee_amounts(ds):
    snapshots = {(s.account_id, s.snapshot_date): s.total_value for s in ds.portfolio_snapshots}
    prior = {1: (12, 31), 4: (3, 31), 7: (6, 30), 10: (9, 30)}
    fees = [t for t in ds.transactions if t.txn_type == "fee"]
    fee_dates = sorted({t.txn_date for t in fees})
    assert len(fee_dates) == 8
    assert fee_dates[0] == date(2024, 10, 15) and fee_dates[-1] == date(2026, 7, 15)
    for t in fees:
        m, d = prior[t.txn_date.month]
        year = t.txn_date.year - 1 if t.txn_date.month == 1 else t.txn_date.year
        base = snapshots[(t.account_id, date(year, m, d))]
        assert t.amount == (base * D("0.0025")).quantize(D("0.01"))


# ---------------------------------------------------------------------------------------------------------------
# Exposures
# ---------------------------------------------------------------------------------------------------------------


def _exposure_weights(ds):
    """{(security_id, exposure_type, as_of): {label: weight}}"""
    grouped = defaultdict(dict)
    for e in ds.security_exposures:
        grouped[(e.security_id, e.exposure_type, e.as_of_date)][e.label] = e.weight_pct
    return grouped


def test_exposure_sums_and_uniqueness(ds):
    keys = [(e.security_id, e.exposure_type, e.label, e.as_of_date) for e in ds.security_exposures]
    assert len(keys) == len(set(keys))
    for weights in _exposure_weights(ds).values():
        assert sum(weights.values()) == D("100.00")
    assert all(e.weight_pct > 0 for e in ds.security_exposures)
    as_of = sorted({e.as_of_date for e in ds.security_exposures})
    assert len(as_of) == 9 and as_of[0] == date(2024, 9, 30) and as_of[-1] == date(2026, 9, 30)


def test_exposure_ranges(ds):
    grouped = _exposure_weights(ds)
    as_of = sorted({e.as_of_date for e in ds.security_exposures})
    for day in as_of:
        assert D("3.00") <= grouped[(201, "sector", day)]["Energy"] <= D("5.00")
        assert grouped[(208, "sector", day)]["Energy"] >= D("90")
        assert "Oil & Gas" in grouped[(201, "industry", day)]
        assert "Oil & Gas" in grouped[(208, "industry", day)]


def test_exposure_drift_bounds(ds):
    from advisor.data.seed import INITIAL_SECTOR_WEIGHTS

    grouped = _exposure_weights(ds)
    as_of = sorted({e.as_of_date for e in ds.security_exposures})
    for sid, initial in INITIAL_SECTOR_WEIGHTS.items():
        series = [grouped[(sid, "sector", day)] for day in as_of]
        assert series[0] == dict(initial)
        assert any(series[i] != series[i + 1] for i in range(len(series) - 1)), sid
        for label, _ in initial[1:]:
            for i in range(len(series) - 1):
                assert abs(series[i + 1][label] - series[i][label]) <= D("0.10"), (sid, label)


def test_industry_rows_sum_to_their_sector(ds):
    from advisor.data.seed import INDUSTRY_SPLITS

    grouped = _exposure_weights(ds)
    for (sid, exposure_type, day), sectors in grouped.items():
        if exposure_type != "sector":
            continue
        industries = grouped[(sid, "industry", day)]
        for sector, weight in sectors.items():
            names = [name for name, _ in INDUSTRY_SPLITS[sector]]
            assert sum(industries[name] for name in names) == weight


# ---------------------------------------------------------------------------------------------------------------
# Golden values (captured once after the invariant tests passed)
# ---------------------------------------------------------------------------------------------------------------


def test_golden_values(ds):
    # golden: changes to seed.py must be deliberate
    closes = _closes(ds)
    sell_105 = next(
        t for t in ds.transactions if t.txn_type == "sell" and (t.account_id, t.txn_date) == (105, date(2026, 9, 14))
    )
    total_101 = next(
        s.total_value for s in ds.portfolio_snapshots if (s.account_id, s.snapshot_date) == (101, date(2026, 9, 30))
    )
    assert fingerprint(ds) == GOLDEN_FINGERPRINT
    assert sum(1 for t in ds.transactions if t.txn_type == "buy") == GOLDEN_BUY_COUNT
    assert closes[(201, date(2026, 9, 30))] == GOLDEN_QXLC_CLOSE_2026_09_30
    assert sell_105.quantity == GOLDEN_ACCOUNT_105_SELL_QTY_2026_09_14
    assert total_101 == GOLDEN_ACCOUNT_101_TOTAL_VALUE_2026_09_30
