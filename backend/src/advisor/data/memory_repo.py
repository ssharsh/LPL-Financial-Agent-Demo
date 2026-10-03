"""In-memory Repository over a Dataset (for tests and Phase 1)."""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from advisor.data.models import (
    Account,
    Advisor,
    AssetClass,
    Client,
    Dataset,
    Holding,
    IdentityRecord,
    PortfolioSnapshot,
    Security,
    SecurityExposure,
    Transaction,
)
from advisor.data.repository import Repository
from advisor.identity import SessionContext


def _in_range(day: date, start_date: date | None, end_date: date | None) -> bool:
    return (start_date is None or day >= start_date) and (end_date is None or day <= end_date)


class MemoryRepository(Repository):
    def __init__(self, dataset: Dataset):
        self._advisors = {a.advisor_id: a for a in dataset.advisors}
        self._clients = {c.client_id: c for c in dataset.clients}
        self._accounts = sorted(dataset.accounts, key=lambda a: a.account_id)
        self._holdings = sorted(dataset.holdings, key=lambda h: h.holding_id)
        self._transactions = sorted(dataset.transactions, key=lambda t: t.transaction_id)
        self._snapshots = sorted(dataset.portfolio_snapshots, key=lambda s: (s.account_id, s.snapshot_date))
        self._asset_classes = sorted(dataset.asset_classes, key=lambda c: c.asset_class_id)
        self._securities = sorted(dataset.securities, key=lambda s: s.security_id)
        self._prices = {(p.security_id, p.price_date): p.close_price for p in dataset.security_prices}
        self._exposures = sorted(dataset.security_exposures, key=lambda e: e.exposure_id)

    def lookup_identity(self, client_id: int) -> IdentityRecord | None:
        client = self._clients.get(client_id)
        if client is None:
            return None
        return IdentityRecord(client_id=client.client_id, advisor_id=client.advisor_id)

    def list_client_directory(self) -> list[tuple[int, str]]:
        return [(c.client_id, f"{c.first_name} {c.last_name}") for _, c in sorted(self._clients.items())]

    # -- session-scoped ---------------------------------------------------------------------------------------

    def _owned(self, session: SessionContext, account_ids: Iterable[int] | None) -> set[int]:
        """The session's account IDs, narrowed to `account_ids` if given (foreign IDs drop out)."""
        owned = {a.account_id for a in self._accounts if a.client_id == session.client_id}
        if account_ids is not None:
            owned &= set(account_ids)
        return owned

    def get_client(self, session: SessionContext) -> Client:
        return self._clients[session.client_id]

    def get_advisor(self, session: SessionContext) -> Advisor | None:
        return self._advisors.get(session.advisor_id)

    def list_accounts(self, session: SessionContext) -> list[Account]:
        owned = self._owned(session, None)
        return [a for a in self._accounts if a.account_id in owned]

    def list_holdings(self, session: SessionContext, account_ids: Iterable[int] | None = None) -> list[Holding]:
        owned = self._owned(session, account_ids)
        return [h for h in self._holdings if h.account_id in owned]

    def list_transactions(
        self,
        session: SessionContext,
        account_ids: Iterable[int] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Transaction]:
        owned = self._owned(session, account_ids)
        return [
            t
            for t in self._transactions
            if t.account_id in owned and _in_range(t.txn_date, start_date, end_date)
        ]

    def list_snapshots(
        self,
        session: SessionContext,
        account_ids: Iterable[int] | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PortfolioSnapshot]:
        owned = self._owned(session, account_ids)
        return [
            s
            for s in self._snapshots
            if s.account_id in owned and _in_range(s.snapshot_date, start_date, end_date)
        ]

    # -- reference ---------------------------------------------------------------------------------------------

    def list_asset_classes(self) -> list[AssetClass]:
        return list(self._asset_classes)

    def list_securities(self, security_ids: Iterable[int] | None = None) -> list[Security]:
        if security_ids is None:
            return list(self._securities)
        wanted = set(security_ids)
        return [s for s in self._securities if s.security_id in wanted]

    def get_close_prices(
        self, security_ids: Iterable[int], dates: Iterable[date]
    ) -> dict[tuple[int, date], Decimal]:
        dates = list(dates)
        result: dict[tuple[int, date], Decimal] = {}
        for sid in sorted(set(security_ids)):
            for day in sorted(set(dates)):
                close = self._prices.get((sid, day))
                if close is not None:
                    result[(sid, day)] = close
        return result

    def list_exposures(self, security_ids: Iterable[int] | None = None) -> list[SecurityExposure]:
        if security_ids is None:
            return list(self._exposures)
        wanted = set(security_ids)
        return [e for e in self._exposures if e.security_id in wanted]
