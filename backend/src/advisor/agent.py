"""The Strands agent and the per-request flow: question -> tools -> answer -> log -> envelope.

Every figure in an answer must come from a tool result of the same turn; the model never computes numbers,
never writes SQL, and never writes any part of the log.
"""

from collections.abc import Callable
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from advisor.audit import AuditStore, build_log_record, new_log_id, render_log
from advisor.config import ChatSettings
from advisor.data.repository import Repository
from advisor.envelope import Envelope, build_envelope
from advisor.identity import SessionContext
from advisor.tools.factory import build_tools
from advisor.tools.ledger import RequestLedger

SYSTEM_PROMPT = """\
You answer questions from one signed-in wealth management client about that client's own accounts.

Data access
- You can see only this client's records, and only through the tools. You cannot see other clients, and you \
cannot change any record.
- Call the tools in every turn for any figure you state, even if an earlier turn already showed it.

Numbers
- Every number you state must appear in a tool result from this turn. Copy it exactly. You may add a $ sign and \
thousands separators, but never change the value.
- Never calculate, estimate, round, sum, average, or convert numbers yourself. If a tool does not return the \
figure the client asked for, say that figure is unavailable.
- If a tool returns an error, explain that the data is unavailable and give the tool's reason in plain words.
- State the as-of date of the data you used.
- For performance questions, give the dollar figures first (starting value, ending value, net deposits and \
withdrawals, investment gain), then the single percentage with its exact label from the tool result.

Limits
- Do not give advice, recommendations, or opinions on what the client should do. Do not make predictions, \
forecasts, or projections. When asked for any of these, say that their financial advisor can help with that.
- Keep answers short and plain."""

AgentFactory = Callable[..., Any]


def default_agent_factory(*, tools: list, messages: list, settings: ChatSettings) -> Agent:
    """The real Bedrock-backed agent. No temperature or top_p: the configured model rejects temperature."""
    model = BedrockModel(model_id=settings.bedrock_model_id, region_name=settings.aws_region)
    return Agent(
        model=model,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        messages=list(messages),
        callback_handler=None,
    )


class Conversation:
    """A multi-turn chat for one session. History carries across turns; each turn gets its own ledger, log,
    and sources (D10)."""

    def __init__(
        self,
        session: SessionContext,
        repo: Repository,
        audit_store: AuditStore,
        settings: ChatSettings,
        agent_factory: AgentFactory | None = None,
    ) -> None:
        self.session = session
        self.repo = repo
        self.audit_store = audit_store
        self.settings = settings
        # None = use the module-level default_agent_factory, looked up at call time (tests monkeypatch it).
        self._agent_factory = agent_factory
        self.messages: list = []

    def answer(self, question: str) -> Envelope:
        """Run one turn. Errors propagate: no envelope, no fallback text, no log."""
        factory = self._agent_factory if self._agent_factory is not None else default_agent_factory
        ledger = RequestLedger()
        tools = build_tools(self.session, self.repo, ledger)
        agent = factory(tools=tools, messages=self.messages, settings=self.settings)
        result = agent(question)
        self.messages = list(agent.messages)
        text = str(result).strip()
        log_id = new_log_id()
        record = build_log_record(
            self.session,
            log_id=log_id,
            question=question,
            answer_text=text,
            ledger=ledger,
            model_id=self.settings.bedrock_model_id,
        )
        self.audit_store.put(self.session, record, render_log(record))
        return build_envelope(text, ledger, log_id)


def answer(
    session: SessionContext,
    question: str,
    *,
    repo: Repository,
    audit_store: AuditStore,
    settings: ChatSettings,
    agent_factory: AgentFactory | None = None,
) -> Envelope:
    """Single-turn helper."""
    return Conversation(session, repo, audit_store, settings, agent_factory).answer(question)
