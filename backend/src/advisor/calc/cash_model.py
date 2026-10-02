"""How each transaction type moves cash and position quantity."""

# PROVISIONAL (pending DB teammate): transactions.amount is a positive magnitude and the direction comes from
# txn_type (P8). quantity is likewise stored positive; the position effect comes from txn_type (v2's
# "sell -> quantity -" is read as the position effect, not the stored sign).

from decimal import Decimal

from advisor.data.models import Transaction

_ZERO = Decimal("0")


def cash_effect(txn: Transaction) -> Decimal:
    """Signed change in the account's cash caused by the transaction."""
    # PROVISIONAL (pending DB teammate): amount is a positive magnitude; sign derived from txn_type (P8).
    match txn.txn_type:
        case "deposit" | "sell" | "dividend":
            return txn.amount
        case "withdrawal" | "buy" | "fee":
            return -txn.amount
        case _:
            raise ValueError(f"Unknown transaction type {txn.txn_type!r} (transaction {txn.transaction_id})")


def position_effect(txn: Transaction) -> Decimal:
    """Signed change in units of txn.security_id caused by the transaction."""
    # PROVISIONAL (pending DB teammate): quantity is stored positive; sign derived from txn_type (P8).
    match txn.txn_type:
        case "buy":
            return txn.quantity
        case "sell":
            return -txn.quantity
        case "dividend" | "deposit" | "withdrawal" | "fee":
            return _ZERO
        case _:
            raise ValueError(f"Unknown transaction type {txn.txn_type!r} (transaction {txn.transaction_id})")
