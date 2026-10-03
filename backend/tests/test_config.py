import os

import pytest

from advisor.config import PostgresSettings, load_chat_settings, load_data_settings, load_env_file, require_vars
from advisor.errors import ConfigError, PhaseNotAvailableError

FULL_CHAT_ENV = {
    "DATA_BACKEND": "postgres",
    "AUDIT_BACKEND": "memory",
    "AWS_REGION": "us-east-1",
    "BEDROCK_MODEL_ID": "model-x",
}


def test_chat_settings_empty_env_names_all_four():
    with pytest.raises(ConfigError) as exc:
        load_chat_settings({})
    message = str(exc.value)
    for name in ("DATA_BACKEND", "AUDIT_BACKEND", "AWS_REGION", "BEDROCK_MODEL_ID"):
        assert name in message
    assert "backend/.env" in message


def test_partial_env_names_only_missing():
    with pytest.raises(ConfigError) as exc:
        load_chat_settings({"DATA_BACKEND": "postgres", "AUDIT_BACKEND": "memory"})
    message = str(exc.value)
    assert "AWS_REGION" in message and "BEDROCK_MODEL_ID" in message
    assert "DATA_BACKEND" not in message and "AUDIT_BACKEND" not in message


def test_empty_string_counts_as_missing():
    with pytest.raises(ConfigError) as exc:
        require_vars(["A", "B"], {"A": "", "B": "x"})
    assert str(exc.value) == (
        "Missing required environment variables: A. Set them in backend/.env (see backend/.env.example)."
    )


def test_full_chat_env_loads():
    settings = load_chat_settings({**FULL_CHAT_ENV, **POSTGRES_ENV})
    assert settings.data_backend == "postgres"
    assert settings.audit_backend == "memory"
    assert settings.aws_region == "us-east-1"
    assert settings.bedrock_model_id == "model-x"


def test_data_settings_requires_data_backend():
    with pytest.raises(ConfigError, match="DATA_BACKEND"):
        load_data_settings({})


POSTGRES_ENV = {
    "AWS_REGION": "us-east-1",
    "DB_HOST": "db.example.com",
    "DB_PORT": "5432",
    "DB_NAME": "LPLTeam20",
    "DB_USER": "postgres",
}


def test_postgres_requires_db_vars():
    with pytest.raises(ConfigError) as exc:
        load_data_settings({"DATA_BACKEND": "postgres"})
    for name in ("AWS_REGION", "DB_HOST", "DB_PORT", "DB_NAME", "DB_USER"):
        assert name in str(exc.value)
    with pytest.raises(ConfigError) as exc:
        load_chat_settings({**FULL_CHAT_ENV, "DATA_BACKEND": "postgres"})
    message = str(exc.value)
    assert "DB_HOST" in message and "AWS_REGION" not in message


def test_postgres_settings_load():
    settings = load_data_settings({"DATA_BACKEND": "postgres", **POSTGRES_ENV})
    assert settings.data_backend == "postgres"
    assert settings.postgres == PostgresSettings(
        aws_region="us-east-1", host="db.example.com", port=5432, dbname="LPLTeam20", user="postgres"
    )
    chat = load_chat_settings({**FULL_CHAT_ENV, **POSTGRES_ENV, "DATA_BACKEND": "postgres"})
    assert chat.postgres == settings.postgres


def test_postgres_port_must_be_integer():
    with pytest.raises(ConfigError, match="DB_PORT must be a whole number"):
        load_data_settings({"DATA_BACKEND": "postgres", **POSTGRES_ENV, "DB_PORT": "abc"})


def test_s3_is_phase_5():
    with pytest.raises(PhaseNotAvailableError, match="Phase 5"):
        load_chat_settings({**FULL_CHAT_ENV, **POSTGRES_ENV, "AUDIT_BACKEND": "s3"})


def test_unknown_values_name_allowed_value():
    with pytest.raises(ConfigError, match="Allowed value: postgres") as exc:
        load_data_settings({"DATA_BACKEND": "dynamo"})
    assert not isinstance(exc.value, PhaseNotAvailableError)
    with pytest.raises(ConfigError, match="Allowed value: memory"):
        load_chat_settings({**FULL_CHAT_ENV, **POSTGRES_ENV, "AUDIT_BACKEND": "disk"})


def test_missing_check_runs_before_value_check():
    with pytest.raises(ConfigError) as exc:
        load_chat_settings({"DATA_BACKEND": "postgres"})
    assert not isinstance(exc.value, PhaseNotAvailableError)
    assert "AWS_REGION" in str(exc.value)


def test_load_env_file_does_not_override_shell(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("ADVISOR_TEST_EXISTING=from_file\nADVISOR_TEST_MISSING=filled\n")
    monkeypatch.setenv("ADVISOR_TEST_EXISTING", "from_shell")
    monkeypatch.delenv("ADVISOR_TEST_MISSING", raising=False)
    load_env_file(env_file)
    try:
        assert os.environ["ADVISOR_TEST_EXISTING"] == "from_shell"
        assert os.environ["ADVISOR_TEST_MISSING"] == "filled"
    finally:
        os.environ.pop("ADVISOR_TEST_MISSING", None)
