"""Builds the Repository. The only data source is the LPLTeam20 Postgres database (DATA_BACKEND=postgres)."""

from advisor.config import DataSettings
from advisor.data.memory_repo import MemoryRepository
from advisor.data.repository import Repository
from advisor.errors import ConfigError


def build_repository(settings: DataSettings) -> Repository:
    if settings.data_backend != "postgres" or settings.postgres is None:
        raise ConfigError(
            "DATA_BACKEND=postgres with AWS_REGION, DB_HOST, DB_PORT, DB_NAME, DB_USER is required. "
            "There is no seed or sample data."
        )
    from advisor.data.postgres_loader import load_dataset

    # One read-only load at startup; MemoryRepository only holds that snapshot and applies session scoping.
    return MemoryRepository(load_dataset(settings.postgres))
