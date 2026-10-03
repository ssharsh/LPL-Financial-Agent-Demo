"""get_security_stats: per-security performance and risk statistics for the client's current holdings.

All figures are computed in code from database records:
- security_prices (closing prices) -> price return, high/low, monthly returns, volatility, max drawdown
- holdings (quantity, avg_cost_basis) -> cost basis, unrealized gain/loss
- current market value / weight -> from get_holdings
- securities (expense_ratio, dividend_yield, risk_rating) -> copied as-is
"""

import math
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from advisor.data.repository import Repository
from advisor.errors import DataUnavailableError, ToolArgumentError
from advisor.identity import SessionContext
from advisor.tools import holdings as holdings_tool
from advisor.tools.common import ToolOutput, holding_record_id, money, pct, price, price_record_id
from advisor.tools.ledger import SourceRef

CALCULATION_METHOD = (
    "Per security, from closing prices in the date range: price_return_pct = (end_close / start_close - 1) x 100; "
    "monthly returns = close-to-close % change between consecutive price dates; avg_monthly_return_pct = mean of "
    "those; volatility_monthly_pct = sample standard deviation of those; volatility_annualized_pct = monthly x "
    "sqrt(12); max_drawdown_pct = largest peak-to-trough fall in close; best/worst_month = highest/lowest monthly "
    "return. From holdings: cost_basis = sum(quantity x avg_cost_basis) across accounts; unrealized_gain = "
    "market_value - cost_basis; unrealized_gain_pct = unrealized_gain / cost_basis x 100. market_value and "
    "weight_pct are current values from get_holdings. Ranking is by price_return_pct (highest = best)."
)

_Q2 = Decimal("0.01")


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tickers: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None


def _parse(value: str | None, name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ToolArgumentError(f"{name} must be YYYY-MM-DD, got {value!r}.") from exc


def _d(x: float) -> Decimal:
    return Decimal(str(x))


def run(session: SessionContext, repo: Repository, args: Args) -> ToolOutput:
    start = _parse(args.start_date, "start_date")
    end = _parse(args.end_date, "end_date")

    held = holdings_tool.run(session, repo, holdings_tool.Args()).result["totals"]["by_security"]
    by_ticker = {s["ticker"]: s for s in held}
    if args.tickers:
        wanted = [t.upper() for t in args.tickers]
        missing = [t for t in wanted if t not in by_ticker]
        if missing:
            raise ToolArgumentError(f"Not held by this client: {', '.join(missing)}. Held: {', '.join(by_ticker)}.")
    else:
        wanted = list(by_ticker)

    securities = {s.ticker: s for s in repo.list_securities()}
    lots = repo.list_holdings(session)
    all_prices = getattr(repo, "_prices", {})

    stats = []
    price_ids: list[str] = []
    for ticker in wanted:
        sec = securities[ticker]
        sid = sec.security_id
        series = sorted(
            (d, c)
            for (s, d), c in all_prices.items()
            if s == sid and (start is None or d >= start) and (end is None or d <= end)
        )
        if len(series) < 2:
            continue
        price_ids += [price_record_id(sid, d) for d, _ in series]
        closes = [c for _, c in series]
        first_d, first_c = series[0]
        last_d, last_c = series[-1]

        monthly = [float(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
        mean = sum(monthly) / len(monthly)
        vol = math.sqrt(sum((r - mean) ** 2 for r in monthly) / (len(monthly) - 1)) if len(monthly) > 1 else 0.0
        peak, mdd = closes[0], Decimal("0")
        for c in closes:
            peak = max(peak, c)
            mdd = min(mdd, (c / peak - 1) * 100)
        best_i = max(range(len(monthly)), key=lambda i: monthly[i])
        worst_i = min(range(len(monthly)), key=lambda i: monthly[i])
        hi_d, hi_c = max(series, key=lambda p: p[1])
        lo_d, lo_c = min(series, key=lambda p: p[1])

        my_lots = [h for h in lots if h.security_id == sid]
        cost = sum((h.quantity * h.avg_cost_basis for h in my_lots), Decimal("0"))
        mv = Decimal(by_ticker[ticker]["market_value"])
        gain = mv - cost

        stats.append(
            {
                "ticker": ticker,
                "name": sec.name,
                "start_date": first_d.isoformat(),
                "start_close": price(first_c),
                "end_date": last_d.isoformat(),
                "end_close": price(last_c),
                "price_change": money(last_c - first_c),
                "price_return_pct": pct((last_c / first_c - 1) * 100),
                "high_close": price(hi_c),
                "high_date": hi_d.isoformat(),
                "low_close": price(lo_c),
                "low_date": lo_d.isoformat(),
                "avg_monthly_return_pct": pct(_d(mean)),
                "volatility_monthly_pct": pct(_d(vol)),
                "volatility_annualized_pct": pct(_d(vol * math.sqrt(12))),
                "max_drawdown_pct": pct(mdd),
                "best_month": series[best_i + 1][0].isoformat()[:7],
                "best_month_return_pct": pct(_d(monthly[best_i])),
                "worst_month": series[worst_i + 1][0].isoformat()[:7],
                "worst_month_return_pct": pct(_d(monthly[worst_i])),
                "quantity": by_ticker[ticker]["quantity"],
                "market_value": money(mv),
                "weight_pct": by_ticker[ticker]["weight_pct"],
                "cost_basis": money(cost),
                "avg_cost_per_share": price((cost / sum((h.quantity for h in my_lots), Decimal("0"))).quantize(Decimal("0.0001"))) if my_lots else None,
                "unrealized_gain": money(gain),
                "unrealized_gain_pct": pct(gain / cost * 100) if cost else None,
                "expense_ratio_pct": pct(sec.expense_ratio * 100) if sec.expense_ratio is not None else None,
                "dividend_yield_pct": pct(sec.dividend_yield * 100) if sec.dividend_yield is not None else None,
                "risk_rating_1_to_5": sec.risk_rating,
            }
        )

    if not stats:
        raise DataUnavailableError("Not enough closing prices in that date range to compute statistics.")

    stats.sort(key=lambda r: Decimal(r["price_return_pct"]), reverse=True)
    for i, r in enumerate(stats, 1):
        r["rank_by_price_return"] = i

    period_start = min(r["start_date"] for r in stats)
    period_end = max(r["end_date"] for r in stats)
    return ToolOutput(
        result={
            "period": {"start_date": period_start, "end_date": period_end},
            "best_performer": stats[0]["ticker"],
            "worst_performer": stats[-1]["ticker"],
            "rows": stats,
        },
        sources=[
            SourceRef(
                type="security_price",
                description=f"Closing prices {period_start} to {period_end}",
                as_of=date.fromisoformat(period_end),
                record_ids=tuple(price_ids),
            ),
            SourceRef(
                type="holding",
                description="Current holdings records (quantity, average cost basis)",
                as_of=date.fromisoformat(period_end),
                record_ids=tuple(holding_record_id(h.holding_id) for h in lots),
            ),
        ],
        calculation_method=CALCULATION_METHOD,
    )
