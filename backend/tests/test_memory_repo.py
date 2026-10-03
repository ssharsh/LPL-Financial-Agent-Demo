import inspect
from datetime import date

import pytest

from advisor.config import DataSettings
from advisor.data.factory import build_repository
from advisor.data.memory_repo import MemoryRepository
from advisor.data.repository import Repository
from advisor.errors import ConfigError

OWNED = {1: {101, 102, 103}, 2: {104, 105}, 3: {106, 107}}
SESSION_METHODS = (
    "get_client",
    "get_advisor",
    "list_accounts",
    "list_holdings",
    "list_transactions",
    "list_snapshots",
)
FORBIDDEN_PARAMS = {"client_id", "customer_id", "advisor_id", "owner"}


@pytest.mark.parametrize("client_id", [1, 2, 3])
def test_session_scoped_methods_return_only_own_rows(seed_repo, session_for, client_id):
    session = session_for(client_id)
    owned = OWNED[client_id]
    accounts = seed_repo.list_accounts(session)
    assert {a.account_id for a in accounts} == owned
    assert all(a.client_id == client_id for a in accounts)
    holdings = seed_repo.list_holdings(session)
    transactions = seed_repo.list_transactions(session)
    snapshots = seed_repo.list_snapshots(session)
    assert holdings and transactions and snapshots
    assert {h.account_id for h in holdings} == owned
    assert {t.account_id for t in transactions} == owned
    assert {s.account_id for s in snapshots} == owned


@pytest.mark.parametrize("client_id", [1, 2, 3])
def test_foreign_account_ids_yield_nothing(seed_repo, session_for, client_id):
    session = session_for(client_id)
    foreign = set().union(*(ids for cid, ids in OWNED.items() if cid != client_id)) | {999}
    assert seed_repo.list_holdings(session, account_ids=foreign) == []
    assert seed_repo.list_transactions(session, account_ids=foreign) == []
    assert seed_repo.list_snapshots(session, account_ids=foreign) == []


def test_account_ids_narrow_within_own_accounts(seed_repo, session_for):
    session = session_for(1)
    assert {h.account_id for h in seed_repo.list_holdings(session, account_ids=[102, 104])} == {102}
    assert {s.account_id for s in seed_repo.list_snapshots(session, account_ids=[101])} == {101}


def test_date_filters_are_inclusive(seed_repo, session_for):
    session = session_for(2)
    txns = seed_repo.list_transactions(session, start_date=date(2026, 9, 14), end_date=date(2026, 9, 15))
    assert [(t.txn_type, t.txn_date) for t in txns] == [
        ("sell", date(2026, 9, 14)),
        ("withdrawal", date(2026, 9, 15)),
    ]
    snaps = seed_repo.list_snapshots(session, start_date=date(2026, 9, 30), end_date=date(2026, 9, 30))
    assert [(s.account_id, s.snapshot_date) for s in snaps] == [(104, date(2026, 9, 30)), (105, date(2026, 9, 30))]


def test_results_are_sorted(seed_repo, session_for):
    session = session_for(3)
    txns = seed_repo.list_transactions(session)
    assert [t.transaction_id for t in txns] == sorted(t.transaction_id for t in txns)
    snaps = seed_repo.list_snapshots(session)
    assert [(s.account_id, s.snapshot_date) for s in snaps] == sorted((s.account_id, s.snapshot_date) for s in snaps)


def test_reference_data(seed_repo):
    assert [c.asset_class_id for c in seed_repo.list_asset_classes()] == [1, 2, 3, 4, 5]
    assert [s.ticker for s in seed_repo.list_securities([208, 201])] == ["QXLC", "QXEN"]
    prices = seed_repo.get_close_prices([201, 999], [date(2026, 9, 30), date(2026, 10, 1)])
    assert list(prices) == [(201, date(2026, 9, 30))]
    exposures = seed_repo.list_exposures([206])
    assert exposures and all(e.security_id == 206 for e in exposures)


def test_lookup_identity(seed_repo):
    record = seed_repo.lookup_identity(3)
    assert (record.client_id, record.advisor_id) == (3, 2)
    assert seed_repo.lookup_identity(99) is None


def _abstract_methods():
    return {name: getattr(Repository, name) for name in Repository.__abstractmethods__}


def test_repository_methods_take_no_owner_parameters():
    for name, method in _abstract_methods().items():
        params = list(inspect.signature(method).parameters)[1:]  # skip self
        if name == "lookup_identity":
            assert params == ["client_id"]
            continue
        assert not FORBIDDEN_PARAMS & set(params), name


def test_session_scoped_methods_take_session_first():
    for name in SESSION_METHODS:
        params = list(inspect.signature(getattr(Repository, name)).parameters)
        assert params[1] == "session", name
    assert set(SESSION_METHODS) <= set(Repository.__abstractmethods__)


def test_build_repository():
    for settings in (DataSettings("memory"), DataSettings("postgres"), DataSettings("other")):
        with pytest.raises(ConfigError, match="There is no seed or sample data"):
            build_repository(settings)


def test_get_client_and_advisor(seed_repo, session_for):
    session = session_for(1)
    client = seed_repo.get_client(session)
    advisor = seed_repo.get_advisor(session)
    assert (client.client_id, client.first_name, client.last_name) == (1, "Elena", "Park")
    assert advisor.advisor_id == session.advisor_id
    assert (advisor.first_name, advisor.last_name) == ("Sarah", "Whitfield")
