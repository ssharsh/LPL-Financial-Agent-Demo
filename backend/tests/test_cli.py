import json

import pytest
from botocore.exceptions import ClientError
from jsonschema import Draft202012Validator

import advisor.agent as agent_module
from advisor.audit import OFFICIAL_RECORD_LINE
from advisor.calc.performance import RETURN_LABEL
from advisor.cli import CREDENTIALS_HINT, _parser, main
from advisor.envelope import ENVELOPE_SCHEMA_PATH
from fake_agent import FakeAgentFactory

DATA_ENV = {"DATA_BACKEND": "memory"}
CHAT_ENV = {
    "DATA_BACKEND": "memory",
    "AUDIT_BACKEND": "memory",
    "AWS_REGION": "us-east-1",
    "BEDROCK_MODEL_ID": "test-model",
}


@pytest.fixture
def fake_factory(monkeypatch):
    factory = FakeAgentFactory(
        script=[("get_performance", {"start_month": "2026-09", "end_month": "2026-09"})],
        answer_text="Net deposits and withdrawals were -$7,700.00.",
    )
    monkeypatch.setattr(agent_module, "default_agent_factory", factory)
    return factory


def test_exactly_four_commands():
    sub = next(a for a in _parser()._actions if a.dest == "command")
    assert set(sub.choices) == {"seed", "tool", "ask", "chat"}


def test_seed(capsys):
    assert main(["seed"], environ=DATA_ENV) == 0
    out = capsys.readouterr().out
    assert "Sarah" in out
    assert "Clients (3):" in out
    assert out.count("      account ") == 7
    assert "Securities (8):" in out
    assert "Postgres load arrives in Phase 3. Nothing was written to any database." in out


def test_tool_get_performance(capsys):
    args = '{"start_month":"2024-10","end_month":"2026-09"}'
    assert main(["tool", "get_performance", "--client-id", "1", "--args", args], environ=DATA_ENV) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["return_label"] == RETURN_LABEL
    assert result["net_flows"] == "36000.00"


def test_tool_without_args(capsys):
    assert main(["tool", "get_accounts", "--client-id", "1"], environ=DATA_ENV) == 0
    assert json.loads(capsys.readouterr().out)["tool"] == "get_accounts"


@pytest.mark.parametrize(
    "argv, expected",
    [
        (["tool", "get_holdings", "--client-id", "1", "--args", '{"account_id":104}'], "Account 104"),
        (["tool", "get_holdings", "--client-id", "1", "--args", '{"client_id":2}'], "client_id"),
        (["tool", "get_accounts", "--client-id", "99"], "Unknown client"),
        (["tool", "get_accounts", "--client-id", "abc"], "whole number"),
        (["tool", "get_holdings", "--client-id", "1", "--args", "[1]"], "JSON object"),
        (["tool", "get_holdings", "--client-id", "1", "--args", "{bad"], "not valid JSON"),
    ],
)
def test_tool_errors(capsys, argv, expected):
    assert main(argv, environ=DATA_ENV) == 1
    err = capsys.readouterr().err
    assert err.startswith("Error: ")
    assert expected in err


def test_ask_missing_aws_settings(capsys):
    env = {"DATA_BACKEND": "memory", "AUDIT_BACKEND": "memory"}
    assert main(["ask", "--client-id", "2", "hi"], environ=env) == 1
    err = capsys.readouterr().err
    assert "AWS_REGION" in err and "BEDROCK_MODEL_ID" in err


@pytest.mark.parametrize("argv", [["seed"], ["tool", "get_accounts", "--client-id", "1"]])
def test_postgres_backend_is_phase3(capsys, argv):
    assert main(argv, environ={"DATA_BACKEND": "postgres"}) == 1
    assert "Phase 3" in capsys.readouterr().err


def test_ask_postgres_is_phase3(capsys):
    assert main(["ask", "--client-id", "2", "hi"], environ={**CHAT_ENV, "DATA_BACKEND": "postgres"}) == 1
    assert "Phase 3" in capsys.readouterr().err


def test_ask_prints_answer_envelope_and_log(capsys, fake_factory):
    assert main(["ask", "--client-id", "2", "How did my accounts do in September 2026?"], environ=CHAT_ENV) == 0
    out = capsys.readouterr().out
    answer_part, rest = out.split("\nEnvelope:\n", 1)
    envelope_part, log_part = rest.split("\nLog:\n", 1)
    assert "Net deposits and withdrawals were -$7,700.00." in answer_part
    envelope = json.loads(envelope_part)
    Draft202012Validator(json.loads(ENVELOPE_SCHEMA_PATH.read_text(encoding="utf-8"))).validate(envelope)
    assert envelope["log_id"].startswith("log_")
    assert envelope["sources"]
    assert envelope["interpretation"] is None and envelope["declined"] is None
    assert envelope["log_id"] in log_part
    assert OFFICIAL_RECORD_LINE in log_part
    assert fake_factory.calls[0]["settings"].bedrock_model_id == "test-model"


def test_chat(capsys, monkeypatch, fake_factory):
    inputs = iter(["", "How did my accounts do in September 2026?", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    assert main(["chat", "--client-id", "2"], environ=CHAT_ENV) == 0
    out = capsys.readouterr().out
    assert "advisor> Net deposits and withdrawals were -$7,700.00." in out
    assert "source: portfolio_snapshot" in out
    assert "  log: log_" in out
    assert len(fake_factory.calls) == 1


def test_chat_ends_on_eof(capsys, monkeypatch, fake_factory):
    def _eof(prompt=""):
        raise EOFError

    monkeypatch.setattr("builtins.input", _eof)
    assert main(["chat", "--client-id", "2"], environ=CHAT_ENV) == 0
    assert fake_factory.calls == []


def test_ask_aws_error_prints_hint(capsys, monkeypatch):
    error = ClientError(
        {"Error": {"Code": "ExpiredTokenException", "Message": "The security token included in the request is expired"}},
        "ConverseStream",
    )
    wrapped = RuntimeError("event loop failed")
    wrapped.__cause__ = error
    monkeypatch.setattr(agent_module, "default_agent_factory", FakeAgentFactory(raise_error=wrapped))
    assert main(["ask", "--client-id", "2", "hi"], environ=CHAT_ENV) == 1
    err = capsys.readouterr().err
    assert "ExpiredTokenException" in err
    assert CREDENTIALS_HINT in err


def test_unrelated_errors_propagate(monkeypatch):
    monkeypatch.setattr(agent_module, "default_agent_factory", FakeAgentFactory(raise_error=KeyError("boom")))
    with pytest.raises(KeyError):
        main(["ask", "--client-id", "2", "hi"], environ=CHAT_ENV)
