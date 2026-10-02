"""Shared pytest fixtures. No test may call Bedrock."""

import pytest

from advisor.data.memory_repo import MemoryRepository
from advisor.data.seed import generate_dataset
from advisor.identity import resolve_identity


@pytest.fixture(autouse=True)
def _block_bedrock(monkeypatch):
    """Make any Bedrock model call fail loudly inside tests."""
    from strands.models.bedrock import BedrockModel

    def _blocked(*args, **kwargs):
        raise RuntimeError("Bedrock calls are not allowed in tests")

    monkeypatch.setattr(BedrockModel, "stream", _blocked)


@pytest.fixture(scope="session")
def seed_dataset():
    return generate_dataset()


@pytest.fixture
def seed_repo(seed_dataset):
    return MemoryRepository(seed_dataset)


@pytest.fixture
def session_for(seed_repo):
    """session_for(client_id) -> SessionContext resolved through dev-mode identity."""

    def _session_for(client_id: int):
        return resolve_identity(seed_repo, mode="dev", credential=str(client_id))

    return _session_for
