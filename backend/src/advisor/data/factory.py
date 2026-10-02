"""Builds the Repository selected by DATA_BACKEND."""

from advisor.config import DataSettings
from advisor.data.memory_repo import MemoryRepository
from advisor.data.repository import Repository
from advisor.data.seed import generate_dataset
from advisor.errors import ConfigError, PhaseNotAvailableError


def build_repository(settings: DataSettings) -> Repository:
    if settings.data_backend == "memory":
        return MemoryRepository(generate_dataset())
    if settings.data_backend == "postgres":
        raise PhaseNotAvailableError(
            "DATA_BACKEND=postgres: the Postgres backend arrives in Phase 3. Use DATA_BACKEND=memory for now."
        )
    raise ConfigError(f"DATA_BACKEND={settings.data_backend!r} is not supported. Allowed value: memory.")
