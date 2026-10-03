"""Tiny HTTP layer for the demo frontend. Reuses the agent exactly as the CLI does.

Run (from backend/):
    .venv/bin/uvicorn --factory advisor.server:create_app --app-dir src --host 127.0.0.1 --port 8000

DEMO ONLY: unauthenticated, dev-mode identity (the client ID comes from the request or DEMO_CLIENT_ID).
Bind to 127.0.0.1 only. Conversations live in memory and are lost on restart.

Endpoints:
    GET  /api/health                      -> {"status": "ok", "chat_configured", "chat_config_error", ...}
    POST /api/chat {message, conversation_id?, client_id?} -> the envelope JSON, unchanged
    GET  /api/portfolio[?client_id=N]     -> client, totals, accounts, holdings, performance, charts
    GET  /api/clients                     -> {"clients": [{"client_id", "name"}], "default_client_id"} (demo picker)
Errors are always {"error": "<message>"}.
"""
import asyncio
import json
import logging
import os
import threading
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from advisor import agent
from advisor.audit import build_audit_store
from advisor.calc.months import format_month, next_month, parse_month
from advisor.charts import allocation_chart, performance_chart, safe_chart
from botocore.exceptions import ClientError, NoCredentialsError

from advisor.config import load_chat_settings, load_data_settings, load_env_file
from advisor.data.factory import build_repository
from advisor.data.repository import Repository
from advisor.errors import AdvisorError, ConfigError, DataUnavailableError, IdentityError
from advisor.identity import SessionContext, resolve_identity
from advisor.tools import holdings as holdings_tool
from advisor.tools.factory import build_tools, call_tool
from advisor.tools.ledger import RequestLedger

logger = logging.getLogger("advisor.server")

CREDENTIALS_HINT = "If this is ExpiredToken or InvalidClientTokenId, refresh your AWS credentials."


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


MAX_MESSAGE_CHARS = 2000
MAX_CONVERSATION_ID_CHARS = 100


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    message: str
    conversation_id: str = "default"
    client_id: str | None = None

    @field_validator("message")
    @classmethod
    def _message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be empty")
        if len(value) > MAX_MESSAGE_CHARS:
            raise ValueError(f"message must be at most {MAX_MESSAGE_CHARS} characters")
        return value

    @field_validator("conversation_id")
    @classmethod
    def _conversation_id(cls, value: str) -> str:
        if not value or len(value) > MAX_CONVERSATION_ID_CHARS:
            raise ValueError(f"conversation_id must be 1 to {MAX_CONVERSATION_ID_CHARS} characters")
        return value


class _Busy(Exception):
    """The conversation is already answering a question."""


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


def _validation_message(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors(include_url=False):
        loc = ".".join(str(p) for p in err["loc"])
        msg = err["msg"].removeprefix("Value error, ")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "Invalid request: " + "; ".join(parts)


def _client_names(repo: Repository, session: SessionContext) -> dict[str, Any]:
    client = repo.get_client(session)
    advisor = repo.get_advisor(session)
    return {
        "client_id": session.client_id,
        "name": f"{client.first_name} {client.last_name}",
        "advisor_name": f"{advisor.first_name} {advisor.last_name}" if advisor else None,
    }


def create_app(
    environ: Mapping[str, str] | None = None,
    *,
    agent_factory: agent.AgentFactory | None = None,
    chat_timeout_seconds: float = 90.0,
    repo=None,
) -> Starlette:
    if environ is None:
        load_env_file()
        environ = os.environ
    if repo is None:  # Tests inject a repository; the app always loads LPLTeam20 from Postgres.
        repo = build_repository(load_data_settings(environ))  # Fails at startup if Postgres settings are missing.
    chat_settings = None
    chat_config_error: str | None = None
    store = None
    try:
        chat_settings = load_chat_settings(environ)
        store = build_audit_store(chat_settings)
    except ConfigError as exc:
        chat_settings, chat_config_error = None, str(exc)
    default_client_id = environ.get("DEMO_CLIENT_ID") or "1"

    conversations: dict[tuple[int, str], tuple[agent.Conversation, threading.Lock]] = {}
    conversations_lock = threading.Lock()
    chat_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="chat")

    def _conversation(session, conversation_id: str) -> tuple[agent.Conversation, threading.Lock]:
        key = (session.client_id, conversation_id)
        with conversations_lock:
            if key not in conversations:
                conv = agent.Conversation(session, repo, store, chat_settings, agent_factory)
                conversations[key] = (conv, threading.Lock())
            return conversations[key]

    async def health(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "chat_configured": chat_settings is not None,
                "chat_config_error": chat_config_error,
                "default_client_id": default_client_id,
            }
        )

    async def chat(request: Request) -> JSONResponse:
        try:
            body = json.loads(await request.body())
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error(400, "Request body must be JSON.")
        if not isinstance(body, dict):
            return _error(400, "Request body must be a JSON object.")
        try:
            req = ChatRequest.model_validate(body)
        except ValidationError as exc:
            return _error(400, _validation_message(exc))
        if chat_settings is None:
            return _error(503, f"Chat is not configured: {chat_config_error}")
        try:
            session = resolve_identity(repo, mode="dev", credential=req.client_id or default_client_id)
        except IdentityError as exc:
            return _error(400, str(exc))
        conv, lock = _conversation(session, req.conversation_id)

        def run():
            if not lock.acquire(blocking=False):
                raise _Busy()
            try:
                return conv.answer(req.message)
            finally:
                lock.release()

        # run_in_executor (not anyio's threadpool) so wait_for can stop waiting while the thread finishes.
        future = asyncio.get_running_loop().run_in_executor(chat_executor, run)
        try:
            envelope = await asyncio.wait_for(future, timeout=chat_timeout_seconds)
        except _Busy:
            return _error(409, "This conversation is still answering the previous question. Please wait.")
        except (TimeoutError, asyncio.TimeoutError):
            return _error(504, "The assistant took too long to answer. Please try again.")
        except AdvisorError as exc:
            return _error(500, str(exc))
        except Exception as exc:
            aws_error = _find_aws_error(exc)
            if aws_error is not None:
                return _error(502, f"{_aws_error_message(aws_error)} {CREDENTIALS_HINT}")
            logger.exception("Unexpected error answering a chat message")
            return _error(500, "Internal server error")
        return JSONResponse(envelope.model_dump(mode="json"))

    async def clients(request: Request) -> JSONResponse:
        # DEMO ONLY: the dev-mode client picker. Dev identity already lets the caller choose any client ID.
        return JSONResponse(
            {
                "clients": [{"client_id": cid, "name": name} for cid, name in repo.list_client_directory()],
                "default_client_id": default_client_id,
            }
        )

    def portfolio(request: Request) -> JSONResponse:
        # Sync endpoint: Starlette runs it in a threadpool.
        try:
            session = resolve_identity(
                repo, mode="dev", credential=request.query_params.get("client_id") or default_client_id
            )
        except IdentityError as exc:
            return _error(400, str(exc))
        try:
            tools = build_tools(session, repo, RequestLedger())
            accounts = call_tool(tools, "get_accounts", {})
            holdings = call_tool(tools, "get_holdings", {})
            perf = None
            try:
                first, last = holdings_tool._valid_month_range(session, repo, repo.list_accounts(session))
                start = format_month(next_month(parse_month(first)))
                perf = call_tool(tools, "get_performance", {"start_month": start, "end_month": last})
            except DataUnavailableError:
                logger.warning("No performance period for client %s", session.client_id)
        except AdvisorError as exc:
            return _error(500, str(exc))

        rows_by_ticker: dict[str, dict[str, Any]] = {}
        for row in holdings["rows"]:
            rows_by_ticker.setdefault(row["ticker"], row)
        holding_list = [
            {
                "ticker": sec["ticker"],
                "name": rows_by_ticker.get(sec["ticker"], {}).get("name", sec["ticker"]),
                "asset_class": rows_by_ticker.get(sec["ticker"], {}).get("asset_class"),
                "market_value": sec["market_value"],
                "weight_pct": sec["weight_pct"],
            }
            for sec in holdings["totals"]["by_security"]
        ]
        holding_list.sort(key=lambda h: Decimal(h["market_value"]), reverse=True)

        perf_keys = (
            "start_value",
            "end_value",
            "net_flows",
            "investment_gain",
            "time_weighted_return_pct",
            "return_label",
        )
        performance = None
        if perf is not None:
            performance = {
                "start_month": perf["period"]["start_month"],
                "end_month": perf["period"]["end_month"],
                **{k: perf.get(k) for k in perf_keys},
            }
        # dict(...) keywords, not string keys: the data-boundary test reserves table-name string literals.
        return JSONResponse(
            dict(
                client=_client_names(repo, session),
                data_as_of=accounts["data_as_of"],
                totals=accounts["totals"],
                accounts=[
                    {k: a[k] for k in ("account_id", "account_name", "account_type", "total_value")}
                    for a in accounts["rows"]
                ],
                holdings=holding_list,
                performance=performance,
                charts={
                    "performance": safe_chart(performance_chart, perf) if perf is not None else None,
                    "allocation": safe_chart(allocation_chart, holdings),
                },
            )
        )

    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return _error(exc.status_code, exc.detail)

    return Starlette(
        routes=[
            Route("/api/health", health, methods=["GET"]),
            Route("/api/chat", chat, methods=["POST"]),
            Route("/api/portfolio", portfolio, methods=["GET"]),
            Route("/api/clients", clients, methods=["GET"]),
        ],
        exception_handlers={HTTPException: http_error},
    )
