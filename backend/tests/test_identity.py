import pytest

from advisor.errors import IdentityError, UnknownClientError
from advisor.identity import SessionContext, resolve_identity


@pytest.mark.parametrize("client_id, advisor_id", [(1, 1), (2, 1), (3, 2)])
def test_dev_mode_resolves_seed_clients(seed_repo, client_id, advisor_id):
    session = resolve_identity(seed_repo, mode="dev", credential=str(client_id))
    assert session == SessionContext(client_id=client_id, advisor_id=advisor_id)


def test_unknown_client(seed_repo):
    with pytest.raises(UnknownClientError, match="Unknown client ID 99"):
        resolve_identity(seed_repo, mode="dev", credential="99")


@pytest.mark.parametrize("credential", ["abc", "", "-1", "1.0", " 1"])
def test_non_numeric_client_id(seed_repo, credential):
    with pytest.raises(IdentityError, match="Client ID must be a whole number") as exc:
        resolve_identity(seed_repo, mode="dev", credential=credential)
    assert not isinstance(exc.value, UnknownClientError)


@pytest.mark.parametrize("credential", ["1", "token", ""])
def test_production_mode_always_fails_closed(seed_repo, credential):
    with pytest.raises(IdentityError, match="failing closed"):
        resolve_identity(seed_repo, mode="production", credential=credential)


def test_session_context_is_frozen():
    session = SessionContext(client_id=1, advisor_id=1)
    with pytest.raises(AttributeError):
        session.client_id = 2
