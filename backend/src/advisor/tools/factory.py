"""Per-session Strands tools. Identity is bound in the closures; no tool parameter names a client or owner."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError
from strands import tool
from strands.tools.decorator import DecoratedFunctionTool

from advisor.data.models import TxnType
from advisor.data.repository import Repository
from advisor.errors import ToolArgumentError
from advisor.identity import SessionContext
from advisor.tools import accounts, holdings, performance, prices, stats, transactions
from advisor.tools.common import ToolOutput
from advisor.tools.ledger import RequestLedger

# PROVISIONAL (pending DB teammate): v2 has no documents table, so there is no get_documents tool (P2).
TOOL_NAMES = ("get_accounts", "get_holdings", "get_transactions", "get_performance", "get_price_history", "get_security_stats", "flag_advice_request")

RunFn = Callable[[SessionContext, Repository, Any], ToolOutput]


def _validation_message(name: str, exc: ValidationError) -> str:
    parts = []
    for err in exc.errors(include_url=False):
        loc = ".".join(str(p) for p in err["loc"])
        parts.append(f"{loc}: {err['msg']}" if loc else err["msg"])
    return f"Invalid arguments for {name}: " + "; ".join(parts)


def build_tools(
    session: SessionContext, repo: Repository, ledger: RequestLedger
) -> list[DecoratedFunctionTool]:
    """The four fact tools bound to this session. Every call that reaches here is recorded in `ledger`."""

    def _invoke(name: str, args_model: type[BaseModel], run: RunFn, kwargs: dict[str, Any]) -> dict[str, Any]:
        try:
            args = args_model.model_validate(kwargs)
        except ValidationError as exc:
            error = ToolArgumentError(_validation_message(name, exc))
            ledger.record(tool=name, arguments=kwargs, status="error", error=str(error))
            raise error from exc
        validated = args.model_dump()
        try:
            output = run(session, repo, args)
            result = {
                **output.result,
                "calculation_method": output.calculation_method,
                "sources": [s.to_json() for s in output.sources],
            }
            if "status" in result and "content" in result:
                raise RuntimeError(f"{name} result must not have both 'status' and 'content' keys")
        except Exception as exc:
            ledger.record(tool=name, arguments=validated, status="error", error=str(exc))
            raise
        ledger.record(
            tool=name,
            arguments=validated,
            status="success",
            result=result,
            sources=tuple(output.sources),
            calculation_method=output.calculation_method,
        )
        return result

    @tool
    def get_accounts() -> dict:
        """List the client's accounts with type, name, objective, cash balance, and latest total value.

        Totals across accounts are included. All amounts are strings in dollars.
        """
        return _invoke("get_accounts", accounts.Args, accounts.run, {})

    @tool
    def get_holdings(as_of_month: str | None = None, account_id: int | None = None) -> dict:
        """Positions, cash, market values, and weights, with totals by account, security, and asset class.

        Args:
            as_of_month: Month-end to value positions at, as YYYY-MM. Omit for the most recent data date.
            account_id: One of the client's account IDs. Omit for all of the client's accounts.
        """
        return _invoke(
            "get_holdings",
            holdings.Args,
            holdings.run,
            {"as_of_month": as_of_month, "account_id": account_id},
        )

    @tool
    def get_transactions(
        start_date: str,
        end_date: str,
        txn_type: TxnType | None = None,
        account_id: int | None = None,
    ) -> dict:
        """Transactions between two dates (inclusive) with signed cash effects and totals by type.

        Args:
            start_date: First date to include, as YYYY-MM-DD.
            end_date: Last date to include, as YYYY-MM-DD. Must not be after the data as-of date.
            txn_type: Only this transaction type. Omit for all types.
            account_id: One of the client's account IDs. Omit for all of the client's accounts.
        """
        return _invoke(
            "get_transactions",
            transactions.Args,
            transactions.run,
            {"start_date": start_date, "end_date": end_date, "txn_type": txn_type, "account_id": account_id},
        )

    @tool
    def get_performance(start_month: str, end_month: str, account_id: int | None = None) -> dict:
        """Start and end value, net deposits/withdrawals, investment gain, and the time-weighted return.

        The return is a monthly Modified Dietz time-weighted return, linked across months (cumulative).

        Args:
            start_month: First month of the period, as YYYY-MM.
            end_month: Last month of the period, as YYYY-MM.
            account_id: One of the client's account IDs. Omit for all accounts combined.
        """
        return _invoke(
            "get_performance",
            performance.Args,
            performance.run,
            {"start_month": start_month, "end_month": end_month, "account_id": account_id},
        )

    @tool
    def get_price_history(
        tickers: list[str] | None = None,
        top_n: int | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Closing price over time for securities the client holds. Use this for any chart or question about
        how a stock/fund's price moved, e.g. "graph my top 3 stocks". A line chart (one line per ticker) is
        produced automatically from the result.
        Args:
            tickers: Tickers to include (must be held by the client). Omit to use the top holdings.
            top_n: When tickers is omitted, how many top holdings by market value to include (default 3).
            start_date: First date to include, as YYYY-MM-DD. Omit for all history.
            end_date: Last date to include, as YYYY-MM-DD. Omit for all history.
        """
        return _invoke(
            "get_price_history",
            prices.Args,
            prices.run,
            {"tickers": tickers, "top_n": top_n, "start_date": start_date, "end_date": end_date},
        )

    @tool
    def get_security_stats(
        tickers: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict:
        """Per-holding performance and risk statistics, ranked best to worst by price return. Use for "best/worst
        performing stocks", returns per stock, volatility, risk, drawdown, best/worst month, gain/loss vs cost
        basis, unrealized gains, expense ratio, dividend yield, or comparing holdings. All figures are computed
        for you; copy them exactly. A bar chart of price return by ticker is produced automatically.
        Args:
            tickers: Tickers to include (must be held by the client). Omit for all holdings.
            start_date: First date to include, as YYYY-MM-DD. Omit for all history.
            end_date: Last date to include, as YYYY-MM-DD. Omit for all history.
        """
        return _invoke(
            "get_security_stats",
            stats.Args,
            stats.run,
            {"tickers": tickers, "start_date": start_date, "end_date": end_date},
        )

    @tool
    def flag_advice_request(topic: str) -> dict:
        """Call this whenever the client asks for investment advice, a recommendation, an opinion on what to do,
        or a prediction/forecast (e.g. "should I sell VTI?", "what should I buy?", "will the market go up?").
        It shows the client a button to set up a meeting with their advisor. Still decline the advice in words.
        Args:
            topic: One short sentence summarizing what advice the client asked for.
        """
        result = {"flagged": True, "topic": topic}
        ledger.record(tool="flag_advice_request", arguments={"topic": topic}, status="success", result=result)
        return result

    return [
        get_accounts,
        get_holdings,
        get_transactions,
        get_performance,
        get_price_history,
        get_security_stats,
        flag_advice_request,
    ]


def call_tool(tools: list[DecoratedFunctionTool], name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call one tool directly (no model), as the CLI does. Rejects unknown tools and argument keys."""
    by_name = {t.tool_name: t for t in tools}
    if name not in by_name:
        raise ToolArgumentError(f"Unknown tool {name!r}. Available tools: {', '.join(TOOL_NAMES)}.")
    if not isinstance(args, dict):
        raise ToolArgumentError(f"Arguments for {name} must be a JSON object.")
    schema = by_name[name].tool_spec["inputSchema"]["json"]
    allowed = list(schema.get("properties", {}))
    unknown = sorted(set(args) - set(allowed))
    if unknown:
        raise ToolArgumentError(
            f"Unknown argument(s) for {name}: {', '.join(unknown)}. "
            f"Allowed: {', '.join(allowed) if allowed else '(none)'}."
        )
    missing = [k for k in schema.get("required", []) if k not in args]
    if missing:
        raise ToolArgumentError(f"Missing required argument(s) for {name}: {', '.join(missing)}.")
    return by_name[name](**args)
