import time

import pytest
from botocore.exceptions import ClientError
from starlette.testclient import TestClient

from advisor.server import create_app
from advisor.tools.factory import build_tools, call_tool
from advisor.tools.ledger import RequestLedger
from advisor.data.memory_repo import MemoryRepository
from fake_agent import FakeAgentFactory, FakeResult
from seed_data import generate_dataset

CHAT_ENV = {
    "DATA_BACKEND": "postgres",
    "AUDIT_BACKEND": "memory",
    "AWS_REGION": "us-east-1",
    "BEDROCK_MODEL_ID": "test-model",
    "DB_HOST": "db.example.com",
    "DB_PORT": "5432",
    "DB_NAME": "LPLTeam20",
    "DB_USER": "postgres",
}
ENVELOPE_KEYS = {"text", "interpretation", "sources", "chart", "log_id", "verification", "declined"}


def client_for(factory=None, environ=CHAT_ENV, **kwargs):
    # Tests inject an in-memory fixture repository; the real app always loads from Postgres.
    kwargs.setdefault("repo", MemoryRepository(generate_dataset()))
    return TestClient(create_app(dict(environ), agent_factory=factory, **kwargs))


def test_health():
    resp = client_for().get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["chat_configured"] is True
    assert body["chat_config_error"] is None
    assert body["default_client_id"] == "1"


def test_chat_happy_path_returns_envelope_with_chart():
    factory = FakeAgentFactory(script=[("get_holdings", {})], answer_text="You hold four asset classes.")
    resp = client_for(factory).post("/api/chat", json={"message": "What do I hold?"})
    assert resp.status_code == 200
    env = resp.json()
    assert set(env) == ENVELOPE_KEYS
    assert env["text"] == "You hold four asset classes."
    assert env["sources"]
    assert env["chart"]["type"] == "pie"
    assert env["log_id"].startswith("log_")


def test_history_threads_per_conversation_id():
    factory = FakeAgentFactory(script=[("get_accounts", {})])
    client = client_for(factory)
    for conv_id in ("a", "a", "b"):
        assert client.post("/api/chat", json={"message": "hi", "conversation_id": conv_id}).status_code == 200
    assert factory.calls[0]["messages"] == []
    assert factory.calls[1]["messages"]
    assert factory.calls[2]["messages"] == []


def test_client_id_in_body_routes_to_that_client(seed_repo, session_for):
    factory = FakeAgentFactory(script=[("get_accounts", {})])
    resp = client_for(factory).post("/api/chat", json={"message": "accounts?", "client_id": "2"})
    assert resp.status_code == 200
    expected = call_tool(build_tools(session_for(2), seed_repo, RequestLedger()), "get_accounts", {})
    assert [a["account_id"] for a in expected["rows"]] == [104, 105]
    assert resp.json()["chart"]["rows"] == [
        {"account_name": a["account_name"], "total_value": a["total_value"]} for a in expected["rows"]
    ]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"json": {}},
        {"json": {"message": "   "}},
        {"json": {"message": "x" * 2001}},
        {"json": ["not", "an", "object"]},
        {"content": b"not json", "headers": {"content-type": "application/json"}},
        {"json": {"message": "hi", "client_id": "999"}},
        {"json": {"message": "hi", "client_id": "abc"}},
    ],
)
def test_chat_bad_requests(kwargs):
    resp = client_for(FakeAgentFactory()).post("/api/chat", **kwargs)
    assert resp.status_code == 400
    assert isinstance(resp.json()["error"], str) and resp.json()["error"]


def test_chat_not_configured_but_portfolio_works():
    client = client_for(environ={"DATA_BACKEND": "postgres"})
    resp = client.post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 503
    assert "AUDIT_BACKEND" in resp.json()["error"]
    health = client.get("/api/health").json()
    assert health["chat_configured"] is False
    assert health["chat_config_error"]
    assert client.get("/api/portfolio").status_code == 200


def test_unexpected_error_is_500_json():
    resp = client_for(FakeAgentFactory(raise_error=RuntimeError("boom"))).post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 500
    assert resp.json() == {"error": "Internal server error"}


def test_aws_error_is_502():
    err = ClientError({"Error": {"Code": "ExpiredToken", "Message": "x"}}, "ConverseStream")
    resp = client_for(FakeAgentFactory(raise_error=err)).post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 502
    assert "ExpiredToken" in resp.json()["error"]


class _SlowAgent:
    def __init__(self, messages):
        self.messages = list(messages)

    def __call__(self, question):
        time.sleep(0.5)
        return FakeResult("late")


def test_timeout_is_504():
    factory = lambda *, tools, messages, settings: _SlowAgent(messages)  # noqa: E731
    started = time.monotonic()
    resp = client_for(factory, chat_timeout_seconds=0.1).post("/api/chat", json={"message": "hi"})
    assert resp.status_code == 504
    assert "too long" in resp.json()["error"]
    assert time.monotonic() - started < 0.45


def test_unknown_route_is_json_404():
    resp = client_for().get("/api/nope")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_portfolio_client_1(seed_repo, session_for):
    resp = client_for().get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert body["client"] == {"client_id": 1, "name": "Elena Park", "advisor_name": "Sarah Whitfield"}
    tools = build_tools(session_for(1), seed_repo, RequestLedger())
    accounts = call_tool(tools, "get_accounts", {})
    assert body["totals"] == accounts["totals"]
    assert body["data_as_of"] == "2026-09-30"
    assert [a["account_id"] for a in body["accounts"]] == [101, 102, 103]
    values = [float(h["market_value"]) for h in body["holdings"]]
    assert values == sorted(values, reverse=True)
    assert all(h["name"] and h["asset_class"] for h in body["holdings"])
    assert body["performance"]["start_month"] == "2024-10"
    assert body["performance"]["end_month"] == "2026-09"
    assert body["performance"]["end_value"] == accounts["totals"]["total_value"]
    perf_chart = body["charts"]["performance"]
    assert perf_chart["type"] == "line" and len(perf_chart["rows"]) == 24
    assert "Cash" in {r["asset_class"] for r in body["charts"]["allocation"]["rows"]}


def test_clients_lists_every_client_sorted(seed_repo):
    resp = client_for().get("/api/clients")
    assert resp.status_code == 200
    body = resp.json()
    assert body["default_client_id"] == "1"
    assert body["clients"][0] == {"client_id": 1, "name": "Elena Park"}
    assert {"client_id": 3, "name": "Priya Raman"} in body["clients"]
    ids = [c["client_id"] for c in body["clients"]]
    assert ids == sorted(ids) and len(ids) == len(set(ids))
    assert set(body["clients"][0]) == {"client_id", "name"}


def test_portfolio_other_client_and_bad_client():
    client = client_for()
    assert client.get("/api/portfolio?client_id=3").json()["client"]["name"] == "Priya Raman"
    resp = client.get("/api/portfolio?client_id=999")
    assert resp.status_code == 400
    assert "999" in resp.json()["error"]
