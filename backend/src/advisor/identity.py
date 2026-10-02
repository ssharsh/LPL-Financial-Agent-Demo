"""Who is asking. A SessionContext is the only source of client identity for data access."""

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from advisor.errors import IdentityError, UnknownClientError

if TYPE_CHECKING:
    from advisor.data.repository import Repository

_CLIENT_ID_RE = re.compile(r"^[0-9]+$")


# PROVISIONAL (pending DB teammate): v2 has no firm concept, so the session carries only the client and the
# client's advisor (P1).
@dataclass(frozen=True, slots=True)
class SessionContext:
    client_id: int
    advisor_id: int


def resolve_identity(
    repo: "Repository", *, mode: Literal["dev", "production"], credential: str
) -> SessionContext:
    """Build the SessionContext. This is the only place app code creates one.

    dev: `credential` is the client ID typed on the CLI; the advisor is looked up. Unknown client -> error.
    production: stub that always fails closed until verified login tokens exist.
    """
    # PROVISIONAL (pending DB teammate): dev identity takes the client ID from the CLI and looks up advisor_id;
    # production identity is a stub that always raises (P1).
    if mode == "dev":
        if not isinstance(credential, str) or not _CLIENT_ID_RE.match(credential):
            raise IdentityError("Client ID must be a whole number")
        client_id = int(credential)
        record = repo.lookup_identity(client_id)
        if record is None:
            raise UnknownClientError(f"Unknown client ID {client_id}")
        return SessionContext(client_id=record.client_id, advisor_id=record.advisor_id)
    if mode == "production":
        # Stub: production identity (verified login token) is not built yet. Fail closed.
        raise IdentityError("Production identity (verified login token) is not implemented; failing closed.")
    raise IdentityError(f"Unknown identity mode {mode!r}")
