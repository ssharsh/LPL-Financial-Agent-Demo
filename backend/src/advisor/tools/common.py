"""Helpers shared by the fact tools: canonical JSON, hashing, number formatting, ownership, data as-of."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal
from typing import TYPE_CHECKING, Any

from advisor.data.models import Account
from advisor.data.repository import Repository
from advisor.errors import AccountAccessError, DataConsistencyError, DataUnavailableError
from advisor.identity import SessionContext

if TYPE_CHECKING:
    from advisor.tools.ledger import SourceRef

_CENT = Decimal("0.01")
_PRICE_MAX_PLACES = 4


@dataclass(frozen=True, slots=True)
class ToolOutput:
    result: dict[str, Any]  # JSON-safe; numbers as strings
    sources: list["SourceRef"]
    calculation_method: str


# -- canonical JSON and hashing -------------------------------------------------------------------------------


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


# -- number formatting (every number leaves a tool as a string) -------------------------------------------------


def _plain(value: Decimal) -> str:
    if value.is_zero():
        value = abs(value)  # never show "-0.00"
    return format(value, "f")


def money(value: Decimal) -> str:
    """Dollars, 2 decimal places (half-even)."""
    return _plain(value.quantize(_CENT, rounding=ROUND_HALF_EVEN))


def pct(value: Decimal) -> str:
    """A percentage value (already x100), 2 decimal places (half-even)."""
    return _plain(value.quantize(_CENT, rounding=ROUND_HALF_EVEN))


def quantity(value: Decimal) -> str:
    """Units without trailing zeros or exponent: 100.0000 -> '100', 12.5000 -> '12.5'."""
    return _plain(value.normalize())


def price(value: Decimal) -> str:
    """At least 2 and at most 4 decimal places. More than 4 places is an error (prices are NUMERIC(12,4))."""
    normalized = value.normalize()
    places = -normalized.as_tuple().exponent
    if places > _PRICE_MAX_PLACES:
        raise ValueError(f"Price {value} has more than {_PRICE_MAX_PLACES} decimal places")
    if places < 2:
        normalized = normalized.quantize(_CENT)
    return _plain(normalized)


def weight_pct(part: Decimal, whole: Decimal) -> str | None:
    """part / whole * 100 at 2 decimal places; None when whole is zero (a weight is undefined)."""
    if whole.is_zero():
        return None
    return pct(part / whole * 100)


# -- record IDs ---------------------------------------------------------------------------------------------


def account_record_id(account_id: int) -> str:
    return str(account_id)


def holding_record_id(holding_id: int) -> str:
    return str(holding_id)


def transaction_record_id(transaction_id: int) -> str:
    return str(transaction_id)


def snapshot_record_id(account_id: int, snapshot_date: date) -> str:
    return f"{account_id}@{snapshot_date.isoformat()}"


def price_record_id(security_id: int, price_date: date) -> str:
    return f"{security_id}@{price_date.isoformat()}"


# -- scope and data as-of -----------------------------------------------------------------------------------


def account_access_message(account_id: int) -> str:
    # Same text for not-owned and nonexistent accounts (D8: no existence leak).
    return f"Account {account_id} is not one of this client's accounts."


def resolve_account_scope(session: SessionContext, repo: Repository, account_id: int | None) -> list[Account]:
    """All of the session's accounts (account_id None) or exactly the one requested, if the session owns it."""
    accounts = repo.list_accounts(session)
    if account_id is None:
        return accounts
    chosen = [a for a in accounts if a.account_id == account_id]
    if not chosen:
        raise AccountAccessError(account_access_message(account_id))
    return chosen


def data_as_of(session: SessionContext, repo: Repository, accounts: list[Account]) -> date:
    """Latest portfolio snapshot date of the given accounts (D4).

    Current-state records (cash_balance, holdings) are stated as of this date, so a transaction dated after it
    means the stored data contradicts itself -> DataConsistencyError.
    """
    account_ids = [a.account_id for a in accounts]
    if not account_ids:
        raise DataUnavailableError("This client has no accounts.")
    snapshots = repo.list_snapshots(session, account_ids)
    if not snapshots:
        raise DataUnavailableError(
            f"No portfolio snapshots exist for account(s) {', '.join(map(str, account_ids))}."
        )
    as_of = max(s.snapshot_date for s in snapshots)
    later = repo.list_transactions(session, account_ids, start_date=as_of + timedelta(days=1))
    if later:
        ids = ", ".join(str(t.transaction_id) for t in later)
        raise DataConsistencyError(
            f"Transactions ({ids}) are dated after the latest portfolio snapshot {as_of.isoformat()}; current "
            "records cannot be stated as of a single date."
        )
    return as_of
