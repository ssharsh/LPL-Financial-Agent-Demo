"""Error hierarchy. Every expected failure is an AdvisorError with a message naming what is wrong."""


class AdvisorError(Exception):
    """Base class for all expected backend errors."""


class ConfigError(AdvisorError):
    """Missing or invalid configuration."""


class PhaseNotAvailableError(ConfigError):
    """A configured option belongs to a later phase."""


class IdentityError(AdvisorError):
    """The caller's identity could not be established."""


class UnknownClientError(IdentityError):
    """The client ID does not exist."""


class ToolArgumentError(AdvisorError):
    """A tool was called with invalid arguments."""


class AccountAccessError(ToolArgumentError):
    """The account is not one of the session client's accounts (or does not exist)."""


class DataUnavailableError(AdvisorError):
    """Requested data does not exist (missing snapshot or price, or a date beyond the data)."""


class DataConsistencyError(AdvisorError):
    """Stored data contradicts itself."""


class LogNotFoundError(AdvisorError):
    """The log does not exist for this client."""
