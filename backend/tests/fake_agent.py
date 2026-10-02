"""A scripted stand-in for the Strands agent. It calls the real tools directly; no model, no Bedrock."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeResult:
    text: str

    def __str__(self) -> str:
        return self.text


@dataclass
class FakeAgent:
    tools: list
    messages: list
    script: list[tuple[str, dict[str, Any]]]
    answer_text: str
    raise_error: Exception | None = None
    tool_errors: list[str] = field(default_factory=list)

    def __call__(self, question: str) -> FakeResult:
        if self.raise_error is not None:
            raise self.raise_error
        by_name = {t.tool_name: t for t in self.tools}
        self.messages.append({"role": "user", "content": [{"text": question}]})
        for name, kwargs in self.script:
            try:
                by_name[name](**kwargs)
            except Exception as exc:  # Strands turns tool exceptions into error tool results
                self.tool_errors.append(str(exc))
        self.messages.append({"role": "assistant", "content": [{"text": self.answer_text}]})
        return FakeResult("  " + self.answer_text + "\n")


class FakeAgentFactory:
    """Records what each call received; builds a FakeAgent per turn."""

    def __init__(self, script=(), answer_text="Scripted answer.", raise_error=None):
        self.script = list(script)
        self.answer_text = answer_text
        self.raise_error = raise_error
        self.calls: list[dict[str, Any]] = []
        self.agents: list[FakeAgent] = []

    def __call__(self, *, tools, messages, settings):
        self.calls.append({"tools": tools, "messages": list(messages), "settings": settings})
        agent = FakeAgent(
            tools=tools,
            messages=list(messages),
            script=self.script,
            answer_text=self.answer_text,
            raise_error=self.raise_error,
        )
        self.agents.append(agent)
        return agent
