"""Postgres loader: unit tests with a fake connection (no network), plus an opt-in live test.

Live test: RUN_POSTGRES_TESTS=1 .venv/bin/python -m pytest tests/test_postgres_loader.py
(reads backend/.env; needs valid AWS credentials; SELECT only).
"""

import os
from datetime import date
from decimal import Decimal

import psycopg2
import pytest

from advisor.config import PostgresSettings, load_data_settings, load_env_file
from advisor.data import postgres_loader
from advisor.data.factory import build_repository
from advisor.data.memory_repo import MemoryRepository
from advisor.data.models import Account, Client
from advisor.data.postgres_loader import (
    DATASET_ENTITIES,
    PostgresLoadError,
    connect,
    read_dataset,
    select_statement,
)
from advisor.data.schema_map import ENTITY_MAPS
from advisor.identity import resolve_identity

SETTINGS = PostgresSettings(aws_region="us-east-1", host="db.example.com", port=5432, dbname="X", user="u")

ROWS = {
    "advisors": [(7, "Ada", "Lovelace", "ada@example.com")],
    "customers": [(3, 7, "Grace", "Hopper", "g@example.com", "moderate", "advanced", date(2020, 1, 1))],
    "accounts": [(30, 3, "brokerage", "Main", date(2020, 1, 2), Decimal("0"), None)],
}


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, statement):
        table = next(e.table for e in ENTITY_MAPS.values() if f'FROM "{e.table}"' in self.conn.rendered(statement))
        if table in self.conn.fail_tables:
            raise psycopg2.errors.UndefinedTable(f'relation "{table}" does not exist')
        self.conn.statements.append(self.conn.rendered(statement))
        self.rows = ROWS.get(table, [])

    def fetchall(self):
        return self.rows


class FakeConn:
    def __init__(self, fail_tables=()):
        self.statements = []
        self.fail_tables = set(fail_tables)

    @staticmethod
    def rendered(statement):
        # Composed.as_string needs a real connection; render identifiers and literals by hand.
        from psycopg2 import sql

        def render(part):
            if isinstance(part, sql.Composed):
                return "".join(render(p) for p in part.seq)
            if isinstance(part, sql.Identifier):
                return ".".join(f'"{s}"' for s in part.strings)
            if isinstance(part, sql.Literal):
                return repr(part.wrapped)
            return part.string

        return render(statement)

    def cursor(self):
        return FakeCursor(self)


def test_read_dataset_maps_rows_to_models():
    conn = FakeConn()
    dataset = read_dataset(conn)
    assert dataset.clients == (
        Client(3, 7, "Grace", "Hopper", "g@example.com", "moderate", "advanced", date(2020, 1, 1)),
    )
    assert dataset.accounts == (Account(30, 3, "brokerage", "Main", date(2020, 1, 2), Decimal("0"), None),)
    assert dataset.holdings == ()
    assert len(conn.statements) == len(DATASET_ENTITIES)
    assert all(s.startswith("SELECT ") for s in conn.statements)


def test_select_statements_use_schema_map_names():
    client_sql = FakeConn.rendered(select_statement("client", ("client_id",)))
    assert client_sql == (
        'SELECT "customer_id", "advisor_id", "first_name", "last_name", "email", "risk_tolerance", '
        '"financial_literacy", "client_since" FROM "customers" ORDER BY "customer_id"'
    )
    account_sql = FakeConn.rendered(select_statement("account", ("account_id",)))
    assert 'COALESCE("cash_balance", 0)' in account_sql
    assert 'FROM "accounts"' in account_sql


def test_missing_table_names_the_table():
    with pytest.raises(PostgresLoadError, match="Could not read table 'holdings'"):
        read_dataset(FakeConn(fail_tables={"holdings"}))


def test_connect_uses_fresh_token_per_attempt_and_reports_failure(monkeypatch):
    tokens = iter(["token-1", "token-2"])
    passwords = []

    def fake_connect(**kwargs):
        passwords.append(kwargs["password"])
        assert kwargs["sslmode"] == "require"
        raise psycopg2.OperationalError("could not translate host name\nmore detail")

    monkeypatch.setattr(postgres_loader, "_auth_token", lambda settings: next(tokens))
    monkeypatch.setattr(postgres_loader.psycopg2, "connect", fake_connect)
    with pytest.raises(PostgresLoadError) as exc:
        connect(SETTINGS)
    assert passwords == ["token-1", "token-2"]
    message = str(exc.value)
    assert "db.example.com:5432/X" in message and "cluster endpoint" in message
    assert "token-" not in message


def test_connect_sets_read_only_session(monkeypatch):
    class Conn:
        session = None

        def set_session(self, **kwargs):
            self.session = kwargs

    monkeypatch.setattr(postgres_loader, "_auth_token", lambda settings: "t")
    monkeypatch.setattr(postgres_loader.psycopg2, "connect", lambda **kwargs: Conn())
    assert connect(SETTINGS).session == {"readonly": True, "autocommit": True}


def test_auth_failure_hints_at_credentials(monkeypatch):
    def fake_connect(**kwargs):
        raise psycopg2.OperationalError('FATAL:  PAM authentication failed for user "u"')

    monkeypatch.setattr(postgres_loader, "_auth_token", lambda settings: "t")
    monkeypatch.setattr(postgres_loader.psycopg2, "connect", fake_connect)
    with pytest.raises(PostgresLoadError, match="AWS credentials may be missing or expired"):
        connect(SETTINGS)


@pytest.mark.skipif(os.environ.get("RUN_POSTGRES_TESTS") != "1", reason="set RUN_POSTGRES_TESTS=1 for the live DB")
def test_live_postgres_repository():
    load_env_file()
    env = {**os.environ, "DATA_BACKEND": "postgres"}
    repo = build_repository(load_data_settings(env))
    assert isinstance(repo, MemoryRepository)
    session = resolve_identity(repo, mode="dev", credential="1")
    client = repo.get_client(session)
    assert (client.first_name, client.last_name) != ("Elena", "Park")
    accounts = repo.list_accounts(session)
    assert accounts and all(a.client_id == 1 for a in accounts)
    own_ids = {a.account_id for a in accounts}
    foreign = next(
        a.account_id
        for cid in range(2, 11)
        for a in repo.list_accounts(resolve_identity(repo, mode="dev", credential=str(cid)))
    )
    assert foreign not in own_ids
    assert repo.list_holdings(session, [foreign]) == []
    assert repo.get_advisor(session) is not None
    assert repo.list_snapshots(session)
