"""Command line tool for testing the backend from the shell.

    PYTHONPATH=src .venv/bin/python -m advisor.cli seed
    PYTHONPATH=src .venv/bin/python -m advisor.cli tool get_accounts --client-id 1 [--args JSON]
    PYTHONPATH=src .venv/bin/python -m advisor.cli ask --client-id 2 "How did my accounts do in September 2026?"
    PYTHONPATH=src .venv/bin/python -m advisor.cli chat --client-id 3

seed and tool make no model call. ask and chat call Bedrock.
"""

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence

from botocore.exceptions import ClientError, NoCredentialsError

from advisor import agent
from advisor.audit import build_audit_store
from advisor.config import load_chat_settings, load_data_settings, load_env_file
from advisor.data.factory import build_repository
from advisor.data.seed import generate_dataset, summarize
from advisor.errors import AdvisorError, ToolArgumentError
from advisor.identity import resolve_identity
from advisor.tools.factory import TOOL_NAMES, build_tools, call_tool
from advisor.tools.ledger import RequestLedger

CREDENTIALS_HINT = "If this is ExpiredToken or InvalidClientTokenId, refresh your AWS credentials."


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="advisor.cli", description="Test the advisor backend from the shell.")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("seed", help="Generate the seed data and print a summary (no database write in Phase 1).")

    tool_p = sub.add_parser("tool", help="Call one fact tool directly for a client (no model call).")
    tool_p.add_argument("name", choices=TOOL_NAMES)
    tool_p.add_argument("--client-id", required=True)
    tool_p.add_argument("--args", default="{}", help="Tool arguments as a JSON object.")

    ask_p = sub.add_parser("ask", help="Ask one question as a client; print the answer, envelope, and log.")
    ask_p.add_argument("--client-id", required=True)
    ask_p.add_argument("question")

    chat_p = sub.add_parser("chat", help="Interactive chat as a client.")
    chat_p.add_argument("--client-id", required=True)
    return parser


# -- commands ----------------------------------------------------------------------------------------------


def _cmd_seed(environ: Mapping[str, str]) -> int:
    load_data_settings(environ)
    s = summarize(generate_dataset())
    print(f"Advisors ({len(s.advisors)}):")
    for a in s.advisors:
        print(f"  {a.advisor_id}  {a.first_name} {a.last_name}")
    print(f"Clients ({len(s.clients)}):")
    for c in s.clients:
        print(
            f"  {c.client.client_id}  {c.client.first_name} {c.client.last_name}  "
            f"(advisor {c.advisor.advisor_id} {c.advisor.first_name} {c.advisor.last_name})"
        )
        for acct in c.accounts:
            print(f"      account {acct.account_id}  {acct.account_type}  opened {acct.opened_date.isoformat()}")
    print(f"Securities ({len(s.securities)}):")
    for sec, asset_class in s.securities:
        print(f"  {sec.security_id}  {sec.ticker}  {sec.name}  ({asset_class})")
    print(
        f"Prices: {s.price_count} daily closes, "
        f"{s.price_first_date.isoformat()} to {s.price_last_date.isoformat()}"
    )
    print(
        f"Portfolio snapshots: {s.snapshot_count} ({s.snapshot_month_count} month-ends, "
        f"{s.snapshot_first_date.isoformat()} to {s.snapshot_last_date.isoformat()})"
    )
    print(f"Holdings: {s.holding_count}")
    print(
        f"Exposures: {s.exposure_count} rows, as of "
        + ", ".join(d.isoformat() for d in s.exposure_as_of_dates)
    )
    print(
        f"Transactions ({s.txn_first_date.isoformat()} to {s.txn_last_date.isoformat()}): "
        + ", ".join(f"{t} {n}" for t, n in s.txn_counts_by_type)
    )
    print("Postgres load arrives in Phase 3. Nothing was written to any database.")
    return 0


def _cmd_tool(ns: argparse.Namespace, environ: Mapping[str, str]) -> int:
    settings = load_data_settings(environ)
    repo = build_repository(settings)
    session = resolve_identity(repo, mode="dev", credential=ns.client_id)
    try:
        args = json.loads(ns.args)
    except json.JSONDecodeError as exc:
        raise ToolArgumentError(f"--args is not valid JSON: {exc}") from exc
    if not isinstance(args, dict):
        raise ToolArgumentError("--args must be a JSON object, for example '{\"account_id\": 101}'.")
    tools = build_tools(session, repo, RequestLedger())
    result = call_tool(tools, ns.name, args)
    print(json.dumps(result, indent=2))
    return 0


def _chat_setup(ns: argparse.Namespace, environ: Mapping[str, str]):
    settings = load_chat_settings(environ)
    repo = build_repository(settings)
    store = build_audit_store(settings)
    session = resolve_identity(repo, mode="dev", credential=ns.client_id)
    return settings, repo, store, session


def _cmd_ask(ns: argparse.Namespace, environ: Mapping[str, str]) -> int:
    settings, repo, store, session = _chat_setup(ns, environ)
    envelope = agent.answer(session, ns.question, repo=repo, audit_store=store, settings=settings)
    print("Answer:")
    print(envelope.text)
    print()
    print("Envelope:")
    print(envelope.model_dump_json(indent=2))
    print()
    print("Log:")
    print(store.get_rendered(session, envelope.log_id), end="")
    return 0


def _cmd_chat(ns: argparse.Namespace, environ: Mapping[str, str]) -> int:
    settings, repo, store, session = _chat_setup(ns, environ)
    conversation = agent.Conversation(session, repo, store, settings)
    print(f"Chatting as client {session.client_id}. Type 'exit' or 'quit' to end.")
    while True:
        try:
            line = input("you> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        question = line.strip()
        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            return 0
        envelope = conversation.answer(question)
        print(f"advisor> {envelope.text}")
        for src in envelope.sources:
            print(f"  source: {src.type} | {src.description} | as of {src.as_of}")
        print(f"  log: {envelope.log_id}")


# -- entry point -------------------------------------------------------------------------------------------


def _find_aws_error(exc: BaseException) -> ClientError | NoCredentialsError | None:
    """Strands may wrap Bedrock errors (EventLoopException); search the cause chain."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        if isinstance(current, (ClientError, NoCredentialsError)):
            return current
        seen.add(id(current))
        current = current.__cause__ or current.__context__
    return None


def _aws_error_message(err: ClientError | NoCredentialsError) -> str:
    if isinstance(err, ClientError):
        info = err.response.get("Error", {})
        return f"AWS error {info.get('Code', 'unknown')}: {info.get('Message', str(err))}"
    return f"AWS error: {err}"


def main(argv: Sequence[str] | None = None, *, environ: Mapping[str, str] | None = None) -> int:
    if environ is None:
        load_env_file()
        environ = os.environ
    ns = _parser().parse_args(argv)
    try:
        if ns.command == "seed":
            return _cmd_seed(environ)
        if ns.command == "tool":
            return _cmd_tool(ns, environ)
        try:
            if ns.command == "ask":
                return _cmd_ask(ns, environ)
            return _cmd_chat(ns, environ)
        except AdvisorError:
            raise
        except Exception as exc:
            aws_error = _find_aws_error(exc)
            if aws_error is None:
                raise
            print(_aws_error_message(aws_error), file=sys.stderr)
            print(CREDENTIALS_HINT, file=sys.stderr)
            return 1
    except AdvisorError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
