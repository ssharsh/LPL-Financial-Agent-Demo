"""get_price_history: closing prices over time (security_prices) for securities the client holds.

Securities are picked by ticker, or as the client's top N holdings by current market value (from get_holdings).
Close prices are copied straight from the price records; nothing is calculated.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from advisor.data.repository import Repository
from advisor.errors import DataUnavailableError, ToolArgumentError
from advisor.identity import SessionContext
from advisor.tools import holdings as holdings_tool
from advisor.tools.common import ToolOutput, price, price_record_id
from advisor.tools.ledger import SourceRef

CALCULATION_METHOD = (
    "Closing prices copied from the security price records for each selected security and date in range. "
    "Top-N securities are ranked by current market value from the client's holdings."
)


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tickers: list[str] | None = None
    top_n: int | None = None
    start_date: str | None = None
    end_date: str | None = None


def _parse(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ToolArgumentError(f"{name} must be YYYY-MM-DD, got {value!r}.") from exc


def run(session: SessionContext, repo: Repository, args: Args) -> ToolOutput:
    start = _parse(args.start_date, "start_date")
    end = _parse(args.end_date, "end_date")

    # Current holdings, ranked by market value (largest first).
    held = holdings_tool.run(session, repo, holdings_tool.Args()).result["totals"]["by_security"]
    ranked = sorted(held, key=lambda s: float(s["market_value"]), reverse=True)
    held_tickers = [s["ticker"] for s in ranked]

    if args.tickers:
        wanted = [t.upper() for t in args.tickers]
        not_held = [t for t in wanted if t not in held_tickers]
        if not_held:
            raise ToolArgumentError(
                f"Not held by this client: {', '.join(not_held)}. Held: {', '.join(held_tickers)}."
            )
        tickers = wanted
    else:
        tickers = held_tickers[: args.top_n or 3]

    securities = {s.ticker: s for s in repo.list_securities()}
    ids = {securities[t].security_id: t for t in tickers if t in securities}

    # Every price date on record for these securities, within range.
    all_prices = getattr(repo, "_prices", {})
    dates = sorted(
        {d for (sid, d) in all_prices if sid in ids and (start is None or d >= start) and (end is None or d <= end)}
    )
    closes = repo.get_close_prices(ids.keys(), dates)
    if not closes:
        raise DataUnavailableError("No closing prices on record for those securities in that date range.")

    rows = [
        {"date": d.isoformat(), "ticker": ids[sid], "close_price": price(closes[(sid, d)])}
        for d in dates
        for sid in ids
        if (sid, d) in closes
    ]
    first, last = dates[0], dates[-1]
    return ToolOutput(
        result={
            "tickers": tickers,
            "period": {"start_date": first.isoformat(), "end_date": last.isoformat()},
            "rows": rows,
        },
        sources=[
            SourceRef(
                type="security_price",
                description=f"Closing prices {first.isoformat()} to {last.isoformat()} for {', '.join(tickers)}",
                as_of=last,
                record_ids=tuple(price_record_id(sid, d) for (sid, d) in sorted(closes)),
            )
        ],
        calculation_method=CALCULATION_METHOD,
    )
