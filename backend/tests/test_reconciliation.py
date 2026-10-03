"""P4 reconciliation at the data level: holdings, cash, and snapshots agree with the transactions."""

from collections import defaultdict
from datetime import date

import pytest

from advisor.calc.positions import apply_average_cost, derive_cash, derive_positions

DATA_AS_OF = date(2026, 9, 30)
ACCOUNT_IDS = [101, 102, 103, 104, 105, 106, 107]


@pytest.fixture(scope="module")
def ds():
    from seed_data import generate_dataset

    return generate_dataset()


@pytest.fixture(scope="module")
def closes(ds):
    return {(p.security_id, p.price_date): p.close_price for p in ds.security_prices}


def test_seed_has_the_expected_accounts(ds):
    assert sorted(a.account_id for a in ds.accounts) == ACCOUNT_IDS


@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_derived_units_equal_holdings(ds, account_id):
    derived = {
        sid: qty for (aid, sid), qty in derive_positions(ds.transactions, DATA_AS_OF).items() if aid == account_id
    }
    held = {h.security_id: h.quantity for h in ds.holdings if h.account_id == account_id}
    assert held
    assert derived == held


@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_derived_cash_equals_cash_balance(ds, account_id):
    account = next(a for a in ds.accounts if a.account_id == account_id)
    assert derive_cash(ds.transactions, DATA_AS_OF, [account_id]) == {account_id: account.cash_balance}


def test_every_snapshot_equals_units_times_close_plus_cash(ds, closes):
    checked = 0
    for snapshot in ds.portfolio_snapshots:
        day = snapshot.snapshot_date
        account_txns = [t for t in ds.transactions if t.account_id == snapshot.account_id]
        positions = derive_positions(account_txns, day)
        cash = derive_cash(account_txns, day, [snapshot.account_id])[snapshot.account_id]
        securities_value = sum(qty * closes[(sid, day)] for (_, sid), qty in positions.items())
        assert snapshot.total_value == securities_value + cash, (snapshot.account_id, day)
        checked += 1
    assert checked == 175


@pytest.mark.parametrize("account_id", ACCOUNT_IDS)
def test_holdings_average_cost_and_first_purchased(ds, account_id):
    trades = defaultdict(list)
    for t in ds.transactions:
        if t.account_id == account_id and t.txn_type in ("buy", "sell"):
            trades[t.security_id].append(t)
    for holding in (h for h in ds.holdings if h.account_id == account_id):
        quantity, avg_cost = apply_average_cost(trades[holding.security_id])
        assert quantity == holding.quantity
        assert avg_cost == holding.avg_cost_basis
        first_buy = min(t.txn_date for t in trades[holding.security_id] if t.txn_type == "buy")
        assert holding.first_purchased == first_buy
