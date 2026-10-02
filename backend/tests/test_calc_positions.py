from datetime import date
from decimal import Decimal

import pytest

from advisor.calc.cash_model import cash_effect, position_effect
from advisor.calc.months import (
    is_month_end,
    iter_months,
    month_end,
    next_month,
    parse_iso_date,
    parse_month,
    prev_month,
)
from advisor.calc.positions import apply_average_cost, derive_cash, derive_positions
from advisor.data.models import Transaction

D = Decimal


def txn(tid, txn_type, amount, *, account_id=1, security_id=None, quantity=None, price=None, day=date(2025, 1, 2)):
    return Transaction(
        transaction_id=tid,
        account_id=account_id,
        security_id=security_id,
        txn_type=txn_type,
        quantity=None if quantity is None else D(quantity),
        price=None if price is None else D(price),
        amount=D(amount),
        txn_date=day,
    )


@pytest.mark.parametrize(
    "txn_type, kwargs, expected_cash, expected_units",
    [
        ("deposit", {}, D("100.00"), D("0")),
        ("withdrawal", {}, D("-100.00"), D("0")),
        ("buy", {"security_id": 5, "quantity": "4", "price": "25.00"}, D("-100.00"), D("4")),
        ("sell", {"security_id": 5, "quantity": "4", "price": "25.00"}, D("100.00"), D("-4")),
        ("dividend", {"security_id": 5}, D("100.00"), D("0")),
        ("fee", {}, D("-100.00"), D("0")),
    ],
)
def test_cash_and_position_effects_for_all_six_types(txn_type, kwargs, expected_cash, expected_units):
    t = txn(1, txn_type, "100.00", **kwargs)
    assert cash_effect(t) == expected_cash
    assert position_effect(t) == expected_units


def test_unknown_type_raises():
    t = txn(1, "rebalance", "1.00")
    with pytest.raises(ValueError, match="rebalance"):
        cash_effect(t)
    with pytest.raises(ValueError, match="rebalance"):
        position_effect(t)


def _tiny_ledger():
    return [
        txn(1, "deposit", "1000.00", day=date(2025, 1, 2)),
        txn(2, "buy", "500.00", security_id=7, quantity="10", price="50.00", day=date(2025, 1, 2)),
        txn(3, "dividend", "5.00", security_id=7, day=date(2025, 1, 20)),
        txn(4, "fee", "2.50", day=date(2025, 1, 31)),
        txn(5, "sell", "250.00", security_id=7, quantity="5", price="50.00", day=date(2025, 2, 3)),
        txn(6, "sell", "275.00", security_id=7, quantity="5", price="55.00", day=date(2025, 2, 10)),
        txn(7, "deposit", "200.00", account_id=2, day=date(2025, 1, 5)),
    ]


def test_derive_positions_respects_as_of_and_drops_zero():
    ledger = _tiny_ledger()
    assert derive_positions(ledger, date(2025, 1, 31)) == {(1, 7): D("10")}
    assert derive_positions(ledger, date(2025, 2, 3)) == {(1, 7): D("5")}
    assert derive_positions(ledger, date(2025, 2, 28)) == {}


def test_derive_cash_reads_every_type_and_defaults_zero():
    ledger = _tiny_ledger()
    assert derive_cash(ledger, date(2025, 1, 31), [1, 2, 3]) == {
        1: D("502.50"),
        2: D("200.00"),
        3: D("0.00"),
    }
    assert derive_cash(ledger, date(2025, 2, 28), [1]) == {1: D("1027.50")}


def test_apply_average_cost_buys_then_sell():
    buys = [
        txn(1, "buy", "100.00", security_id=7, quantity="10", price="10.00", day=date(2025, 1, 2)),
        txn(2, "buy", "200.00", security_id=7, quantity="10", price="20.00", day=date(2025, 1, 3)),
    ]
    quantity, avg = apply_average_cost(buys)
    assert quantity == D("20") and str(avg) == "15.0000"
    sell = txn(3, "sell", "125.00", security_id=7, quantity="5", price="25.00", day=date(2025, 1, 4))
    quantity, avg = apply_average_cost(buys + [sell])
    assert quantity == D("15") and str(avg) == "15.0000"


def test_apply_average_cost_orders_by_date_then_id():
    later_sell = txn(1, "sell", "50.00", security_id=7, quantity="5", price="10.00", day=date(2025, 1, 5))
    buy = txn(2, "buy", "100.00", security_id=7, quantity="10", price="10.00", day=date(2025, 1, 2))
    assert apply_average_cost([later_sell, buy]) == (D("5"), D("10.0000"))


def test_apply_average_cost_rejects_mixed_positions():
    with pytest.raises(ValueError):
        apply_average_cost(
            [
                txn(1, "buy", "10.00", security_id=7, quantity="1", price="10.00"),
                txn(2, "buy", "10.00", security_id=8, quantity="1", price="10.00"),
            ]
        )


def test_month_helpers():
    assert parse_month("2026-09") == (2026, 9)
    for bad in ("2026-13", "2026-9", "26-09", "2026-00", "2026-09-01"):
        with pytest.raises(ValueError):
            parse_month(bad)
    assert month_end(2024, 2) == date(2024, 2, 29)
    assert prev_month((2025, 1)) == (2024, 12)
    assert next_month((2024, 12)) == (2025, 1)
    assert list(iter_months((2024, 11), (2025, 2))) == [(2024, 11), (2024, 12), (2025, 1), (2025, 2)]
    assert is_month_end(date(2026, 9, 30)) and not is_month_end(date(2026, 9, 29))
    assert parse_iso_date("2026-09-30") == date(2026, 9, 30)
    for bad in ("2026-9-30", "2026-02-30", "20260930"):
        with pytest.raises(ValueError):
            parse_iso_date(bad)
