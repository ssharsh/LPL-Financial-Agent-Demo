"""Environment configuration.

Mirrors backend/connect_to_db.py: backend/.env is loaded without overriding variables already set in the
shell, and every missing variable is reported in one error. No required variable has a default. Every loader
takes the environment mapping explicitly so tests never read the real .env.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from advisor.errors import ConfigError, PhaseNotAvailableError

BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"


def load_env_file(path: Path = ENV_FILE) -> None:
    """Load a .env file into os.environ. Variables already set in the shell take precedence."""
    load_dotenv(path, override=False)


def require_vars(names: Iterable[str], environ: Mapping[str, str]) -> dict[str, str]:
    """Return the named variables, or raise one ConfigError listing every missing or empty one."""
    names = list(names)
    missing = [name for name in names if not environ.get(name)]
    if missing:
        raise ConfigError(
            f"Missing required environment variables: {', '.join(missing)}. "
            "Set them in backend/.env (see backend/.env.example)."
        )
    return {name: environ[name] for name in names}


POSTGRES_VARS = ("AWS_REGION", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER")


@dataclass(frozen=True, slots=True)
class PostgresSettings:
    """Aurora PostgreSQL connection (IAM database auth: a fresh token per connect, no stored password)."""

    aws_region: str
    host: str
    port: int
    dbname: str
    user: str


@dataclass(frozen=True, slots=True)
class DataSettings:
    data_backend: str
    postgres: PostgresSettings | None = None


@dataclass(frozen=True, slots=True)
class ChatSettings:
    data_backend: str
    audit_backend: str
    aws_region: str
    bedrock_model_id: str
    postgres: PostgresSettings | None = None


def _check_data_backend(value: str) -> str:
    if value == "postgres":
        return value
    raise ConfigError(
        f"DATA_BACKEND={value!r} is not supported. Allowed value: postgres (seed/sample data was removed)."
    )


def _postgres_settings(data_backend: str, environ: Mapping[str, str]) -> PostgresSettings | None:
    """The Postgres connection settings when DATA_BACKEND=postgres, else None."""
    if data_backend != "postgres":
        return None
    values = require_vars(POSTGRES_VARS, environ)
    try:
        port = int(values["DB_PORT"])
    except ValueError:
        raise ConfigError(f"DB_PORT must be a whole number, got {values['DB_PORT']!r}.") from None
    return PostgresSettings(
        aws_region=values["AWS_REGION"],
        host=values["DB_HOST"],
        port=port,
        dbname=values["DB_NAME"],
        user=values["DB_USER"],
    )


def _check_audit_backend(value: str) -> str:
    if value == "memory":
        return value
    if value == "s3":
        raise PhaseNotAvailableError(
            "AUDIT_BACKEND=s3: the S3 audit store arrives in Phase 5. Use AUDIT_BACKEND=memory for now."
        )
    raise ConfigError(f"AUDIT_BACKEND={value!r} is not supported. Allowed value: memory.")


def load_data_settings(environ: Mapping[str, str]) -> DataSettings:
    """Settings for commands that only read data (tool, server)."""
    values = require_vars(["DATA_BACKEND"], environ)
    data_backend = _check_data_backend(values["DATA_BACKEND"])
    return DataSettings(data_backend=data_backend, postgres=_postgres_settings(data_backend, environ))


def load_chat_settings(environ: Mapping[str, str]) -> ChatSettings:
    """Settings for commands that call the model (ask, chat)."""
    values = require_vars(["DATA_BACKEND", "AUDIT_BACKEND", "AWS_REGION", "BEDROCK_MODEL_ID"], environ)
    data_backend = _check_data_backend(values["DATA_BACKEND"])
    return ChatSettings(
        data_backend=data_backend,
        audit_backend=_check_audit_backend(values["AUDIT_BACKEND"]),
        aws_region=values["AWS_REGION"],
        bedrock_model_id=values["BEDROCK_MODEL_ID"],
        postgres=_postgres_settings(data_backend, environ),
    )
