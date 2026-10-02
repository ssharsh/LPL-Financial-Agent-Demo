import pytest
from strands import Agent
from strands.models import BedrockModel

import advisor.agent as agent_module
from advisor.agent import SYSTEM_PROMPT, Conversation, answer, default_agent_factory
from advisor.audit import OFFICIAL_RECORD_LINE, MemoryAuditStore
from advisor.config import ChatSettings
from advisor.tools.factory import TOOL_NAMES, build_tools
from advisor.tools.ledger import RequestLedger
from fake_agent import FakeAgentFactory

SETTINGS = ChatSettings(
    data_backend="memory", audit_backend="memory", aws_region="us-east-1", bedrock_model_id="test-model"
)
SCRIPT = [
    ("get_performance", {"start_month": "2026-09", "end_month": "2026-09"}),
    ("get_holdings", {"account_id": 101}),  # client 2 does not own 101 -> error, no sources
]


@pytest.fixture
def setup(session_for, seed_repo):
    return session_for(2), seed_repo, MemoryAuditStore()


def test_conversation_envelope_and_log(setup):
    session, repo, store = setup
    factory = FakeAgentFactory(script=SCRIPT, answer_text="Net flows were -$7,700.00.")
    conv = Conversation(session, repo, store, SETTINGS, agent_factory=factory)
    env = conv.answer("How did my accounts do in September 2026?")

    assert env.text == "Net flows were -$7,700.00."
    assert env.log_id.startswith("log_")
    assert env.interpretation is None
    assert env.chart is None
    assert env.verification is None
    assert env.declined is None
    assert {(s.type, s.as_of) for s in env.sources} == {
        ("portfolio_snapshot", "2026-09-30"),
        ("transaction", "2026-09-30"),
    }
    assert factory.agents[0].tool_errors and "101" in factory.agents[0].tool_errors[0]

    [stored] = store.list_logs(session)
    assert stored.log_id == env.log_id
    assert stored.json_key.startswith("2/")
    record = store.get_record(session, env.log_id)
    assert record.model_id == "test-model"
    assert [c.tool for c in record.tool_calls] == ["get_performance", "get_holdings"]
    assert [c.status for c in record.tool_calls] == ["success", "error"]
    assert record.answer_text == env.text
    assert OFFICIAL_RECORD_LINE in store.get_rendered(session, env.log_id)


def test_sources_cover_only_this_turn_and_history_carries(setup):
    session, repo, store = setup
    factory = FakeAgentFactory(script=[("get_accounts", {})])
    conv = Conversation(session, repo, store, SETTINGS, agent_factory=factory)
    first = conv.answer("What accounts do I have?")
    factory.script = []
    second = conv.answer("Thanks")

    assert factory.calls[0]["messages"] == []
    assert [m["content"][0]["text"] for m in factory.calls[1]["messages"]] == [
        "What accounts do I have?",
        "Scripted answer.",
    ]
    assert first.sources and second.sources == []
    assert first.log_id != second.log_id
    assert len(store.list_logs(session)) == 2
    assert store.get_record(session, second.log_id).tool_calls == []


def test_errors_propagate_and_store_nothing(setup):
    session, repo, store = setup
    factory = FakeAgentFactory(raise_error=RuntimeError("model down"))
    with pytest.raises(RuntimeError, match="model down"):
        answer(session, "q", repo=repo, audit_store=store, settings=SETTINGS, agent_factory=factory)
    assert store.list_logs(session) == []


def test_module_default_factory_is_looked_up_at_call_time(setup, monkeypatch):
    session, repo, store = setup
    factory = FakeAgentFactory()
    conv = Conversation(session, repo, store, SETTINGS)
    monkeypatch.setattr(agent_module, "default_agent_factory", factory)
    env = conv.answer("hello")
    assert env.text == "Scripted answer."
    assert len(factory.calls) == 1


def test_default_agent_factory_builds_bedrock_agent_without_temperature(session_for, seed_repo):
    tools = build_tools(session_for(1), seed_repo, RequestLedger())
    agent = default_agent_factory(tools=tools, messages=[], settings=SETTINGS)
    assert isinstance(agent, Agent)
    assert agent.system_prompt == SYSTEM_PROMPT
    assert sorted(agent.tool_names) == sorted(TOOL_NAMES)
    assert isinstance(agent.model, BedrockModel)
    config = agent.model.get_config()
    assert config["model_id"] == "test-model"
    assert "temperature" not in config
    assert "top_p" not in config
    assert agent.model.client.meta.region_name == "us-east-1"


def test_system_prompt_covers_rules():
    lowered = SYSTEM_PROMPT.lower()
    for phrase in ["advice", "predictions", "never calculate", "unavailable", "as-of date", "exact label",
                   "other clients", "advisor"]:
        assert phrase in lowered
