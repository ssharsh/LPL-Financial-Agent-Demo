"""Loads the whole dataset from Aurora PostgreSQL once, read-only, into a Dataset.

The sample database is small (~550 rows), so DATA_BACKEND=postgres reads every mapped table at startup and
serves requests from MemoryRepository. Session scoping stays in MemoryRepository; the data is a startup
snapshot (restart the server to refresh).

Every statement is a SELECT built from schema_map (psycopg2.sql.Identifier, no string formatting of names), on a
connection set to read-only. IAM database auth: a fresh token is generated for every connect attempt; the
static DB_PASSWORD is never used.
"""

import boto3
import psycopg2
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError
from psycopg2 import sql

from advisor.config import PostgresSettings
from advisor.data.models import Dataset
from advisor.data.schema_map import ENTITY_MAPS, MODEL_FOR_ENTITY
from advisor.errors import ConfigError

CONNECT_TIMEOUT_SECONDS = 10
CONNECT_ATTEMPTS = 2
CLUSTER_ENDPOINT_HINT = "If DB_HOST is an instance endpoint, try the cluster endpoint instead."
CREDENTIALS_HINT = "AWS credentials may be missing or expired (ExpiredToken / InvalidClientTokenId); refresh them."

# Dataset field -> entity, in Dataset field order. ORDER BY keys are domain fields.
DATASET_ENTITIES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("advisors", "advisor", ("advisor_id",)),
    ("clients", "client", ("client_id",)),
    ("accounts", "account", ("account_id",)),
    ("asset_classes", "asset_class", ("asset_class_id",)),
    ("securities", "security", ("security_id",)),
    ("security_exposures", "security_exposure", ("exposure_id",)),
    ("security_prices", "security_price", ("security_id", "price_date")),
    ("holdings", "holding", ("holding_id",)),
    ("transactions", "transaction", ("transaction_id",)),
    ("portfolio_snapshots", "portfolio_snapshot", ("account_id", "snapshot_date")),
)

# Nullable in the database but required by the model: read as COALESCE(column, default).
COALESCE_DEFAULTS: dict[tuple[str, str], int] = {("account", "cash_balance"): 0}


class PostgresLoadError(ConfigError):
    """The Postgres dataset could not be loaded (connection, credentials, or schema)."""


def _first_line(exc: BaseException) -> str:
    text = str(exc).strip()
    return text.splitlines()[0] if text else type(exc).__name__


def _auth_token(settings: PostgresSettings) -> str:
    try:
        return boto3.client("rds", region_name=settings.aws_region).generate_db_auth_token(
            DBHostname=settings.host, Port=settings.port, DBUsername=settings.user, Region=settings.aws_region
        )
    except (NoCredentialsError, ClientError, BotoCoreError) as exc:
        raise PostgresLoadError(
            f"Could not create an IAM database auth token: {_first_line(exc)}. {CREDENTIALS_HINT}"
        ) from None


def connect(settings: PostgresSettings):
    """A read-only autocommit connection, with a fresh IAM token per attempt and one retry."""
    last_error: psycopg2.OperationalError | None = None
    for _ in range(CONNECT_ATTEMPTS):
        try:
            conn = psycopg2.connect(
                host=settings.host,
                port=settings.port,
                dbname=settings.dbname,
                user=settings.user,
                password=_auth_token(settings),
                sslmode="require",
                connect_timeout=CONNECT_TIMEOUT_SECONDS,
            )
        except psycopg2.OperationalError as exc:
            last_error = exc
            continue
        conn.set_session(readonly=True, autocommit=True)
        return conn
    message = _first_line(last_error)
    hint = CREDENTIALS_HINT if "authentication failed" in message.lower() else CLUSTER_ENDPOINT_HINT
    raise PostgresLoadError(
        f"Could not connect to Postgres at {settings.host}:{settings.port}/{settings.dbname}: {message}. {hint}"
    ) from None


def select_statement(entity: str, order_by: tuple[str, ...]) -> sql.Composed:
    """SELECT <mapped columns> FROM <table> ORDER BY <keys>, names taken from schema_map only."""
    entity_map = ENTITY_MAPS[entity]
    columns = []
    for field, column in entity_map.columns.items():
        ident = sql.Identifier(column)
        default = COALESCE_DEFAULTS.get((entity, field))
        if default is not None:
            ident = sql.SQL("COALESCE({}, {})").format(ident, sql.Literal(default))
        columns.append(ident)
    return sql.SQL("SELECT {cols} FROM {table} ORDER BY {order}").format(
        cols=sql.SQL(", ").join(columns),
        table=sql.Identifier(entity_map.table),
        order=sql.SQL(", ").join(sql.Identifier(entity_map.columns[f]) for f in order_by),
    )


def read_dataset(conn) -> Dataset:
    """Run one SELECT per mapped table on `conn` and build the Dataset."""
    parts = {}
    with conn.cursor() as cur:
        for dataset_field, entity, order_by in DATASET_ENTITIES:
            model = MODEL_FOR_ENTITY[entity]
            fields = list(ENTITY_MAPS[entity].columns)
            try:
                cur.execute(select_statement(entity, order_by))
            except psycopg2.Error as exc:
                raise PostgresLoadError(
                    f"Could not read table {ENTITY_MAPS[entity].table!r}: {_first_line(exc)}"
                ) from None
            parts[dataset_field] = tuple(model(**dict(zip(fields, row))) for row in cur.fetchall())
    return Dataset(**parts)


def load_dataset(settings: PostgresSettings) -> Dataset:
    conn = connect(settings)
    try:
        return read_dataset(conn)
    finally:
        conn.close()
