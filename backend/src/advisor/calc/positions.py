"""Positions, cash, and average cost derived from transactions."""

# PROVISIONAL (pending DB teammate): current positions come from the holdings table; past month-end positions
# are derived from cumulative buy/sell quantities and valued at that date's close (P4). Snapshot total_value
# is assumed to INCLUDE cash (unconfirmed in v2).

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from advisor.calc.cash_model import cash_effect, position_effect
from advisor.data.models import Transaction

_ZERO = Decimal("0")
_CENTS = Decimal("0.00")
_AVG_COST_QUANTUM = Decimal("0.0001")


def derive_positions(transactions: Iterable[Transaction], as_of: date) -> dict[tuple[int, int], Decimal]:
    """Units held per (account_id, security_id) from transactions dated <= as_of. Zero positions are dropped."""
    units: dict[tuple[int, int], Decimal] = {}
    for txn in transactions:
        if txn.txn_date > as_of:
            continue
        effect = position_effect(txn)
        if effect == _ZERO:
            continue
        key = (txn.account_id, txn.security_id)
        units[key] = units.get(key, _ZERO) + effect
    return {key: qty for key, qty in units.items() if qty != _ZERO}


def derive_cash(
    transactions: Iterable[Transaction], as_of: date, account_ids: Iterable[int]
) -> dict[int, Decimal]:
    """Cash per account from transactions dated <= as_of. Accounts with no transactions get 0.00."""
    cash = {account_id: _CENTS for account_id in account_ids}
    for txn in transactions:
        if txn.txn_date > as_of or txn.account_id not in cash:
            continue
        cash[txn.account_id] += cash_effect(txn)
    return cash


def apply_average_cost(transactions: Iterable[Transaction]) -> tuple[Decimal, Decimal]:
    """(quantity, avg_cost_basis per share) for ONE account x security, average-cost method.

    Buys and sells are applied in (txn_date, transaction_id) order. A buy adds its amount to total cost; a sell
    removes total_cost * sold / quantity_before. avg_cost_basis is quantized to 0.0001. Other types are ignored
    for cost (they do not change units).
    """
    ordered = sorted(transactions, key=lambda t: (t.txn_date, t.transaction_id))
    keys = {(t.account_id, t.security_id) for t in ordered if t.txn_type in ("buy", "sell")}
    if len(keys) > 1:
        raise ValueError(f"apply_average_cost expects one account x security, got {sorted(keys)}")
    quantity = _ZERO
    total_cost = _ZERO
    for txn in ordered:
        effect = position_effect(txn)
        if txn.txn_type == "buy":
            total_cost += txn.amount
            quantity += effect
        elif txn.txn_type == "sell":
            if quantity <= _ZERO:
                raise ValueError(f"Sell without a position (transaction {txn.transaction_id})")
            total_cost -= total_cost * txn.quantity / quantity
            quantity += effect
    if quantity == _ZERO:
        raise ValueError("No units remain; average cost is undefined")
    return quantity, (total_cost / quantity).quantize(_AVG_COST_QUANTUM)
