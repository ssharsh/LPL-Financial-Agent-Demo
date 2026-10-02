"""Repository interface.

Client-owned data is only reachable through a SessionContext; no method below takes a raw client ID except
lookup_identity, which only identity.resolve_identity may call. `account_ids` narrows results within the
session's own accounts; IDs the session does not own simply yield nothing (mirrors the future row level
security). Reference data (asset classes, securities, prices, exposures) is not client-owned.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from advisor.data.models import (
    Account,
    AssetClass,
    Holding,
    IdentityRecord,
    PortfolioSnapshot,
    Security,
    SecurityExposure,
    Transaction,
)
from advisor.identity import SessionContext


class Repository(ABC):
    @abstractmethod
    def lookup_identity(self, client_id: int) -> IdentityRecord | None:
        """Client + advisor for a client ID, or None. Only identity.resolve_identity may call this."""

    # -- session-scoped client data --------------------------------------------------------------------------

    @abstractmethod
    def list_accounts(self, session: SessionContext) -> list[Account]:
        """The session client's accounts, sorted by account_id."""

    @abstractmethod
    def list_holdings(
        self, session: SessionContext, account_ids: Iterable[int] | None = None
    ) -> list[Holding]:
        """Current holdings of the session client's accounts, sorted by holding_id."""

    @abstractmethod
    def list_transactions(
        self,
        session: SessionContext,
        account_ids: Iterable[int] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        """Transactions of every type, dates inclusive, sorted by transaction_id."""

    @abstractmethod
    def list_snapshots(
        self,
        session: SessionContext,
        account_ids: Iterable[int] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PortfolioSnapshot]:
        """Portfolio snapshots, dates inclusive, sorted by (account_id, snapshot_date)."""

    # -- reference data --------------------------------------------------------------------------------------

    @abstractmethod
    def list_asset_classes(self) -> list[AssetClass]:
        """All asset classes, sorted by asset_class_id."""

    @abstractmethod
    def list_securities(self, security_ids: Iterable[int] | None = None) -> list[Security]:
        """Securities, sorted by security_id."""

    @abstractmethod
    def get_close_prices(
        self, security_ids: Iterable[int], dates: Iterable[date]
    ) -> dict[tuple[int, date], Decimal]:
        """Close per (security_id, date) for every requested pair that exists; missing pairs are absent."""

    @abstractmethod
    def list_exposures(self, security_ids: Iterable[int] | None = None) -> list[SecurityExposure]:
        """Security exposures, sorted by exposure_id."""
