"""Deterministic demo dataset shaped exactly like the teammate's v2 tables.

What it builds: 2 advisors, 3 clients, 7 accounts opened in September 2024, 8 invented QX-prefixed funds in
5 asset classes, daily closes for every calendar day 2024-09-01..2026-09-30, rule-based transactions, month-end
portfolio snapshots, current holdings, and quarterly sector + industry exposures.

Randomness: one random.Random per purpose (PRICE_SEED for the price walk, EXPOSURE_SEED for quarterly exposure
drift), integer-only randint calls, so the output is identical on every run and Python version. Transactions
are rule-based (no randomness beyond the prices they use).

Cash model: transactions.amount and quantity are stored as positive magnitudes and the direction comes from
txn_type: deposit, sell, and dividend add cash; withdrawal, buy, and fee remove it; buy adds units and sell
removes them. Dividends are paid to cash, not reinvested. The simulation asserts cash never goes negative.

Average cost: per account x security, a buy adds its amount to total cost and its quantity to units; a sell
removes total_cost * sold / units_before from total cost. avg_cost_basis = total_cost / units, per share,
quantized to 0.0001. The seed computes this itself; tests check it against calc.positions.apply_average_cost.

Opening snapshot: every account has a month-end snapshot from 2024-09-30 (the opening month) through
2026-09-30, so performance can start at 2024-10.

Provisional decisions (pending the DB teammate), marked in code with "PROVISIONAL (pending DB teammate)":
  P3 snapshot grain (one per account per calendar month-end), P4 total_value includes cash, P6
  total_contributions left None, P7 the seed itself, P8 amounts/quantities positive with direction from
  txn_type, P9 dividend_yield left None (units undocumented).
"""

# PROVISIONAL (pending DB teammate): the seed data is ours, deterministic, and shaped exactly like the v2 tables
# (all CHECK enums and NUMERIC precisions). Loading it into Postgres is Phase 3 (P7).

import math
import random
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from advisor.data.models import (
    TXN_TYPES,
    Account,
    Advisor,
    AssetClass,
    Client,
    Dataset,
    Holding,
    PortfolioSnapshot,
    Security,
    SecurityExposure,
    SecurityPrice,
    Transaction,
)

PRICE_SEED = 20261002
EXPOSURE_SEED = 20261003

PRICE_START = date(2024, 9, 1)
DATA_END = date(2026, 9, 30)

_CENT = Decimal("0.01")
_AVG_COST_QUANTUM = Decimal("0.0001")
_ZERO = Decimal("0")
_FEE_RATE = Decimal("0.0025")  # 0.25% per quarter of the prior quarter-end snapshot value

# ---------------------------------------------------------------------------------------------------------------
# People and reference data
# ---------------------------------------------------------------------------------------------------------------

ADVISORS = (
    Advisor(1, "Sarah", "Whitfield", "sarah.whitfield@example.com"),
    Advisor(2, "Marcus", "Delgado", "marcus.delgado@example.com"),
)

CLIENTS = (
    Client(1, 1, "Elena", "Park", "elena.park@example.com", "moderate", "intermediate", date(2024, 9, 3)),
    Client(2, 1, "James", "Okafor", "james.okafor@example.com", "conservative", "beginner", date(2024, 9, 5)),
    Client(3, 2, "Priya", "Raman", "priya.raman@example.com", "aggressive", "advanced", date(2024, 9, 10)),
)

ASSET_CLASSES = (
    AssetClass(
        1,
        "US Equity",
        "Shares of U.S. companies, which can grow in value over time but rise and fall with the market.",
        "Growth",
        "#1F6FEB",
    ),
    AssetClass(
        2,
        "Intl Equity",
        "Shares of companies outside the U.S., which add growth potential and spread risk across countries.",
        "Growth",
        "#8957E5",
    ),
    AssetClass(
        3,
        "Bonds",
        "Loans to governments and companies that pay interest and usually move less than stocks.",
        "Stability",
        "#2DA44E",
    ),
    AssetClass(
        4,
        "Real Estate",
        "Shares of property companies, which tend to pay regular income from rents.",
        "Income",
        "#BF8700",
    ),
    AssetClass(
        5,
        "Cash",
        "Money held in cash or cash-like investments, which is stable and easy to access.",
        "Stability",
        "#6E7781",
    ),
)

QXLC, QXSC, QXID, QXEM, QXAG, QXST, QXRE, QXEN = 201, 202, 203, 204, 205, 206, 207, 208

# PROVISIONAL (pending DB teammate): dividend_yield units are undocumented in v2 (expense_ratio is documented as
# a fraction), so expense_ratio is a fraction and dividend_yield is None; no tool reads either (P9).
SECURITIES = (
    Security(
        QXLC, "QXLC", "Northstar US Large Cap Index ETF", "etf", 1, None, "United States",
        Decimal("0.0003"), None, 3,
        "An exchange-traded fund that tracks a broad index of large U.S. companies.",
    ),
    Security(
        QXSC, "QXSC", "Northstar US Small Cap Index ETF", "etf", 1, None, "United States",
        Decimal("0.0005"), None, 4,
        "An exchange-traded fund that tracks an index of smaller U.S. companies.",
    ),
    Security(
        QXID, "QXID", "Meridian Developed Markets Index Fund", "mutual_fund", 2, None, "Developed ex-US",
        Decimal("0.0007"), None, 3,
        "A mutual fund that tracks companies in developed countries outside the U.S.",
    ),
    Security(
        QXEM, "QXEM", "Meridian Emerging Markets Index ETF", "etf", 2, None, "Emerging Markets",
        Decimal("0.0010"), None, 4,
        "An exchange-traded fund that tracks companies in emerging-market countries.",
    ),
    Security(
        QXAG, "QXAG", "Harborline US Aggregate Bond Index Fund", "mutual_fund", 3, None, "United States",
        Decimal("0.0004"), None, 2,
        "A mutual fund that tracks a broad index of U.S. government, mortgage, and corporate bonds.",
    ),
    Security(
        QXST, "QXST", "Harborline Short-Term Treasury Index ETF", "etf", 3, None, "United States",
        Decimal("0.0004"), None, 1,
        "An exchange-traded fund that holds short-term U.S. Treasury bonds.",
    ),
    Security(
        QXRE, "QXRE", "Cedar Peak Real Estate Index ETF", "etf", 4, "Real Estate", "United States",
        Decimal("0.0012"), None, 4,
        "An exchange-traded fund that tracks U.S. real estate companies and REITs.",
    ),
    Security(
        QXEN, "QXEN", "Cedar Peak Energy Sector Index ETF", "etf", 1, "Energy", "United States",
        Decimal("0.0010"), None, 5,
        "An exchange-traded fund that tracks U.S. energy companies.",
    ),
)


@dataclass(frozen=True)
class _PriceSpec:
    start: Decimal
    drift_bps: int
    vol_bps: int


PRICE_SPECS: Mapping[int, _PriceSpec] = {
    QXLC: _PriceSpec(Decimal("100.00"), 3, 90),
    QXSC: _PriceSpec(Decimal("50.00"), 2, 120),
    QXID: _PriceSpec(Decimal("40.00"), 2, 90),
    QXEM: _PriceSpec(Decimal("30.00"), 2, 130),
    QXAG: _PriceSpec(Decimal("25.00"), 1, 25),
    QXST: _PriceSpec(Decimal("20.00"), 1, 6),
    QXRE: _PriceSpec(Decimal("35.00"), 2, 110),
    QXEN: _PriceSpec(Decimal("60.00"), 2, 160),
}

# Dividend per share. Quarterly funds pay on the 20th of Sep/Dec/Mar/Jun, monthly funds on the 25th.
DIVIDEND_PER_SHARE: Mapping[int, Decimal] = {
    QXLC: Decimal("0.32"),
    QXSC: Decimal("0.18"),
    QXID: Decimal("0.35"),
    QXEM: Decimal("0.20"),
    QXAG: Decimal("0.07"),
    QXST: Decimal("0.06"),
    QXRE: Decimal("0.33"),
    QXEN: Decimal("0.55"),
}
MONTHLY_DIVIDEND_FUNDS = frozenset({QXAG, QXST})


@dataclass(frozen=True)
class _AccountSpec:
    account_id: int
    client_id: int
    account_type: str
    account_name: str
    opened_date: date
    objective: str
    opening_deposit: Decimal
    monthly_deposit: Decimal | None
    allocation: Mapping[int, int]  # security_id -> percent of each deposit (sums to 98)


ACCOUNT_SPECS = (
    _AccountSpec(101, 1, "brokerage", "Individual Brokerage", date(2024, 9, 3), "Growth",
                 Decimal("120000.00"), Decimal("1000.00"),
                 {QXLC: 45, QXSC: 10, QXID: 15, QXAG: 20, QXEN: 8}),
    _AccountSpec(102, 1, "roth_ira", "Roth IRA", date(2024, 9, 3), "Retirement",
                 Decimal("45000.00"), Decimal("500.00"),
                 {QXLC: 60, QXID: 20, QXEM: 10, QXRE: 8}),
    _AccountSpec(103, 1, "traditional_ira", "Rollover IRA", date(2024, 9, 3), "Retirement",
                 Decimal("60000.00"), None,
                 {QXAG: 40, QXLC: 35, QXST: 15, QXRE: 8}),
    _AccountSpec(104, 2, "traditional_ira", "Traditional IRA", date(2024, 9, 5), "Income",
                 Decimal("210000.00"), None,
                 {QXAG: 45, QXST: 20, QXLC: 25, QXRE: 8}),
    _AccountSpec(105, 2, "529", "College Savings 529", date(2024, 9, 5), "Education",
                 Decimal("30000.00"), Decimal("300.00"),
                 {QXLC: 50, QXID: 18, QXAG: 30}),
    _AccountSpec(106, 3, "trust", "Raman Family Trust", date(2024, 9, 10), "Growth",
                 Decimal("350000.00"), None,
                 {QXLC: 40, QXSC: 15, QXEM: 15, QXEN: 13, QXRE: 15}),
    _AccountSpec(107, 3, "401k", "Employer 401(k)", date(2024, 9, 10), "Retirement",
                 Decimal("85000.00"), Decimal("1500.00"),
                 {QXLC: 55, QXSC: 15, QXID: 18, QXAG: 10}),
)

MONTHLY_DEPOSIT_DAY = 5
MONTHLY_DEPOSIT_FIRST = (2024, 10)
MONTHLY_DEPOSIT_LAST = (2026, 9)

QUARTERLY_DIVIDEND_MONTHS = frozenset({3, 6, 9, 12})
QUARTERLY_DIVIDEND_DAY = 20
MONTHLY_DIVIDEND_DAY = 25
DIVIDEND_FIRST = date(2024, 9, 1)

FEE_MONTHS = frozenset({1, 4, 7, 10})
FEE_DAY = 15
FEE_FIRST = date(2024, 10, 15)
FEE_LAST = date(2026, 7, 15)

# Events. 101: sell 10% of QXLC and buy QXAG with the proceeds. 106 and 105: sell enough to fund a withdrawal.
REBALANCE_EVENT = (101, date(2025, 12, 10), QXLC, Decimal("0.10"), QXAG)
SELL_TO_RAISE = {
    (106, date(2025, 6, 10)): (QXSC, Decimal("15000")),
    (105, date(2026, 9, 14)): (QXLC, Decimal("8000")),
}
WITHDRAWALS = {
    (106, date(2025, 6, 12)): Decimal("15000.00"),
    (105, date(2026, 9, 15)): Decimal("8000.00"),
}

# ---------------------------------------------------------------------------------------------------------------
# Exposures
# ---------------------------------------------------------------------------------------------------------------

EXPOSURE_DATES = (
    date(2024, 9, 30),
    date(2024, 12, 31),
    date(2025, 3, 31),
    date(2025, 6, 30),
    date(2025, 9, 30),
    date(2025, 12, 31),
    date(2026, 3, 31),
    date(2026, 6, 30),
    date(2026, 9, 30),
)

# Initial sector weights per fund. The first sector listed is the balancing sector (100 - sum of the others).
INITIAL_SECTOR_WEIGHTS: Mapping[int, tuple[tuple[str, Decimal], ...]] = {
    QXLC: (
        ("Information Technology", Decimal("31.00")), ("Financials", Decimal("13.00")),
        ("Health Care", Decimal("11.00")), ("Consumer Discretionary", Decimal("10.50")),
        ("Communication Services", Decimal("9.00")), ("Industrials", Decimal("8.50")),
        ("Consumer Staples", Decimal("5.50")), ("Energy", Decimal("4.00")), ("Utilities", Decimal("2.50")),
        ("Real Estate", Decimal("2.50")), ("Materials", Decimal("2.50")),
    ),
    QXSC: (
        ("Industrials", Decimal("18.00")), ("Financials", Decimal("17.00")), ("Health Care", Decimal("15.00")),
        ("Information Technology", Decimal("13.00")), ("Consumer Discretionary", Decimal("11.00")),
        ("Real Estate", Decimal("6.00")), ("Energy", Decimal("5.00")), ("Materials", Decimal("5.00")),
        ("Consumer Staples", Decimal("3.50")), ("Communication Services", Decimal("3.50")),
        ("Utilities", Decimal("3.00")),
    ),
    QXID: (
        ("Financials", Decimal("22.50")), ("Industrials", Decimal("18.00")), ("Health Care", Decimal("11.00")),
        ("Consumer Discretionary", Decimal("10.00")), ("Information Technology", Decimal("9.00")),
        ("Consumer Staples", Decimal("8.00")), ("Materials", Decimal("6.50")), ("Energy", Decimal("4.50")),
        ("Communication Services", Decimal("4.50")), ("Utilities", Decimal("3.50")),
        ("Real Estate", Decimal("2.50")),
    ),
    QXEM: (
        ("Information Technology", Decimal("24.00")), ("Financials", Decimal("22.00")),
        ("Consumer Discretionary", Decimal("13.00")), ("Communication Services", Decimal("9.00")),
        ("Materials", Decimal("7.00")), ("Industrials", Decimal("6.50")), ("Consumer Staples", Decimal("5.00")),
        ("Energy", Decimal("5.00")), ("Health Care", Decimal("3.50")), ("Utilities", Decimal("3.00")),
        ("Real Estate", Decimal("2.00")),
    ),
    QXAG: (
        ("Government", Decimal("45.00")), ("Securitized", Decimal("27.00")), ("Corporate", Decimal("26.00")),
        ("Cash", Decimal("2.00")),
    ),
    QXST: (("Government", Decimal("98.00")), ("Cash", Decimal("2.00"))),
    QXRE: (("Real Estate", Decimal("98.00")), ("Financials", Decimal("2.00"))),
    QXEN: (("Energy", Decimal("96.00")), ("Utilities", Decimal("2.50")), ("Industrials", Decimal("1.50"))),
}

# Sector -> industries with percent of the sector weight (the last industry takes the remainder).
INDUSTRY_SPLITS: Mapping[str, tuple[tuple[str, int], ...]] = {
    "Information Technology": (("Software", 45), ("Semiconductors", 35), ("Technology Hardware", 20)),
    "Financials": (("Banks", 45), ("Capital Markets", 30), ("Insurance", 25)),
    "Health Care": (("Pharmaceuticals", 50), ("Health Care Equipment", 30), ("Biotechnology", 20)),
    "Consumer Discretionary": (("Retail", 55), ("Automobiles", 25), ("Hotels & Leisure", 20)),
    "Communication Services": (("Interactive Media", 60), ("Telecommunications", 25), ("Entertainment", 15)),
    "Industrials": (("Aerospace & Defense", 35), ("Machinery", 35), ("Transportation", 30)),
    "Consumer Staples": (("Food & Beverage", 55), ("Household Products", 45)),
    "Energy": (("Oil & Gas", 85), ("Energy Equipment & Services", 15)),
    "Utilities": (("Electric Utilities", 80), ("Gas Utilities", 20)),
    "Real Estate": (("REITs", 90), ("Real Estate Services", 10)),
    "Materials": (("Chemicals", 60), ("Metals & Mining", 40)),
    "Government": (("Government Bonds", 100),),
    "Securitized": (("Mortgage-Backed Securities", 100),),
    "Corporate": (("Investment-Grade Corporate Bonds", 100),),
    "Cash": (("Cash & Equivalents", 100),),
}

_MIN_SECTOR_WEIGHT = Decimal("0.10")

# ---------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------


def _cents(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_EVEN)


def _days(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def _is_month_end(day: date) -> bool:
    return (day + timedelta(days=1)).day == 1


def _prior_quarter_end(day: date) -> date:
    """Last day of the calendar quarter before the one containing `day`."""
    quarter_first_month = 3 * ((day.month - 1) // 3) + 1
    return date(day.year, quarter_first_month, 1) - timedelta(days=1)


def _month_key(day: date) -> tuple[int, int]:
    return day.year, day.month


# ---------------------------------------------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------------------------------------------


def _generate_prices() -> dict[tuple[int, date], Decimal]:
    rng = random.Random(PRICE_SEED)
    security_ids = sorted(PRICE_SPECS)
    closes: dict[tuple[int, date], Decimal] = {}
    previous = {sid: PRICE_SPECS[sid].start for sid in security_ids}
    for sid in security_ids:
        closes[(sid, PRICE_START)] = previous[sid]
    for day in _days(PRICE_START + timedelta(days=1), DATA_END):
        for sid in security_ids:
            spec = PRICE_SPECS[sid]
            bps = spec.drift_bps + rng.randint(-spec.vol_bps, spec.vol_bps)
            close = _cents(previous[sid] * (Decimal(10000 + bps) / Decimal(10000)))
            if close <= _ZERO:
                raise ValueError(f"Price walk produced a non-positive close for {sid} on {day}")
            closes[(sid, day)] = close
            previous[sid] = close
    return closes


# ---------------------------------------------------------------------------------------------------------------
# Transactions, snapshots, holdings
# ---------------------------------------------------------------------------------------------------------------


@dataclass
class _Book:
    """Running state of one account during the simulation."""

    cash: Decimal = Decimal("0.00")
    units: dict[int, Decimal] = field(default_factory=dict)
    total_cost: dict[int, Decimal] = field(default_factory=dict)
    first_buy: dict[int, date] = field(default_factory=dict)


class _Simulation:
    def __init__(self, closes: Mapping[tuple[int, date], Decimal]):
        self.closes = closes
        self.books: dict[int, _Book] = {}
        self.transactions: list[Transaction] = []
        self.snapshots: list[PortfolioSnapshot] = []
        self.snapshot_values: dict[tuple[int, date], Decimal] = {}

    # -- recording -------------------------------------------------------------------------------------------

    def _emit(self, account_id, txn_type, amount, txn_date, security_id=None, quantity=None, price=None):
        # PROVISIONAL (pending DB teammate): amount and quantity are stored as positive magnitudes; the direction
        # comes from txn_type (P8).
        if amount <= _ZERO or (quantity is not None and quantity <= _ZERO):
            raise ValueError(f"Non-positive {txn_type} in account {account_id} on {txn_date}")
        book = self.books[account_id]
        match txn_type:
            case "deposit" | "dividend":
                book.cash += amount
            case "withdrawal" | "fee":
                book.cash -= amount
            case "buy":
                book.cash -= amount
                book.units[security_id] = book.units.get(security_id, _ZERO) + quantity
                book.total_cost[security_id] = book.total_cost.get(security_id, _ZERO) + amount
                book.first_buy.setdefault(security_id, txn_date)
            case "sell":
                units_before = book.units[security_id]
                if quantity >= units_before:
                    raise ValueError(f"Seed never fully sells a position ({account_id}, {security_id})")
                book.cash += amount
                book.total_cost[security_id] -= book.total_cost[security_id] * quantity / units_before
                book.units[security_id] = units_before - quantity
            case _:
                raise ValueError(f"Unknown transaction type {txn_type!r}")
        if book.cash < _ZERO:
            raise ValueError(f"Cash went negative in account {account_id} on {txn_date} ({txn_type})")
        self.transactions.append(
            Transaction(
                transaction_id=len(self.transactions) + 1,
                account_id=account_id,
                security_id=security_id,
                txn_type=txn_type,
                quantity=quantity,
                price=price,
                amount=amount,
                txn_date=txn_date,
            )
        )

    def _trade(self, account_id, txn_type, security_id, quantity: int, day):
        close = self.closes[(security_id, day)]
        qty = Decimal(quantity)
        self._emit(account_id, txn_type, qty * close, day, security_id, qty, close)

    # -- one account-day -------------------------------------------------------------------------------------

    def _deposit_amount(self, spec: _AccountSpec, day: date) -> Decimal | None:
        if day == spec.opened_date:
            return spec.opening_deposit
        if (
            spec.monthly_deposit is not None
            and day.day == MONTHLY_DEPOSIT_DAY
            and MONTHLY_DEPOSIT_FIRST <= _month_key(day) <= MONTHLY_DEPOSIT_LAST
        ):
            return spec.monthly_deposit
        return None

    def _dividend_funds(self, book: _Book, day: date) -> list[int]:
        if day < DIVIDEND_FIRST:
            return []
        if day.day == QUARTERLY_DIVIDEND_DAY and day.month in QUARTERLY_DIVIDEND_MONTHS:
            eligible = [sid for sid in DIVIDEND_PER_SHARE if sid not in MONTHLY_DIVIDEND_FUNDS]
        elif day.day == MONTHLY_DIVIDEND_DAY:
            eligible = sorted(MONTHLY_DIVIDEND_FUNDS)
        else:
            return []
        return sorted(sid for sid in eligible if book.units.get(sid, _ZERO) > _ZERO)

    def account_day(self, spec: _AccountSpec, day: date) -> None:
        """All of one account's transactions for one day, in the fixed same-day order:
        deposit, sell, buy, dividend, fee, withdrawal; within a type by security_id."""
        account_id = spec.account_id
        book = self.books[account_id]

        # deposit
        deposit = self._deposit_amount(spec, day)
        if deposit is not None:
            self._emit(account_id, "deposit", deposit, day)

        # sell (and any buy it funds)
        buys: dict[int, int] = {}
        rebalance_account, rebalance_day, sell_sid, sell_fraction, buy_sid = REBALANCE_EVENT
        if (account_id, day) == (rebalance_account, rebalance_day):
            sell_qty = math.floor(book.units[sell_sid] * sell_fraction)
            self._trade(account_id, "sell", sell_sid, sell_qty, day)
            proceeds = self.transactions[-1].amount
            buys[buy_sid] = math.floor(proceeds / self.closes[(buy_sid, day)])
        if (account_id, day) in SELL_TO_RAISE:
            sid, target = SELL_TO_RAISE[(account_id, day)]
            self._trade(account_id, "sell", sid, math.ceil(target / self.closes[(sid, day)]), day)

        # buy
        if deposit is not None:
            for sid, pct in spec.allocation.items():
                qty = math.floor(deposit * pct / 100 / self.closes[(sid, day)])
                if qty == 0:
                    continue
                if sid in buys:
                    raise ValueError(f"Two buys of {sid} in account {account_id} on {day}")
                buys[sid] = qty
        for sid in sorted(buys):
            if buys[sid] > 0:
                self._trade(account_id, "buy", sid, buys[sid], day)

        # dividend
        for sid in self._dividend_funds(book, day):
            amount = _cents(book.units[sid] * DIVIDEND_PER_SHARE[sid])
            self._emit(account_id, "dividend", amount, day, security_id=sid)

        # fee
        if FEE_FIRST <= day <= FEE_LAST and day.day == FEE_DAY and day.month in FEE_MONTHS:
            base = self.snapshot_values[(account_id, _prior_quarter_end(day))]
            self._emit(account_id, "fee", _cents(base * _FEE_RATE), day)

        # withdrawal
        if (account_id, day) in WITHDRAWALS:
            self._emit(account_id, "withdrawal", WITHDRAWALS[(account_id, day)], day)

    # -- snapshots -------------------------------------------------------------------------------------------

    def snapshot(self, account_id: int, day: date) -> None:
        # PROVISIONAL (pending DB teammate): snapshot grain is one row per account per calendar month-end (P3), and
        # total_value = securities at that day's close + cash, i.e. it INCLUDES cash (P4).
        book = self.books[account_id]
        securities_value = sum(
            (qty * self.closes[(sid, day)] for sid, qty in sorted(book.units.items()) if qty > _ZERO),
            _ZERO,
        )
        total_value = _cents(securities_value + book.cash)
        self.snapshot_values[(account_id, day)] = total_value
        # PROVISIONAL (pending DB teammate): total_contributions semantics are undefined, so it is None (P6).
        self.snapshots.append(PortfolioSnapshot(account_id, day, total_value, None))

    def run(self) -> None:
        for day in _days(PRICE_START, DATA_END):
            for spec in ACCOUNT_SPECS:
                if day < spec.opened_date:
                    continue
                self.books.setdefault(spec.account_id, _Book())
                self.account_day(spec, day)
            if _is_month_end(day):
                for spec in ACCOUNT_SPECS:
                    if spec.account_id in self.books:
                        self.snapshot(spec.account_id, day)


def _build_holdings(books: Mapping[int, _Book]) -> list[Holding]:
    holdings: list[Holding] = []
    for account_id in sorted(books):
        book = books[account_id]
        for sid in sorted(book.units):
            qty = book.units[sid]
            if qty <= _ZERO:
                continue
            avg = (book.total_cost[sid] / qty).quantize(_AVG_COST_QUANTUM, rounding=ROUND_HALF_EVEN)
            holdings.append(Holding(len(holdings) + 1, account_id, sid, qty, avg, book.first_buy[sid]))
    return holdings


# ---------------------------------------------------------------------------------------------------------------
# Exposures
# ---------------------------------------------------------------------------------------------------------------


def _industry_rows(sector: str, sector_weight: Decimal) -> list[tuple[str, Decimal]]:
    split = INDUSTRY_SPLITS[sector]
    rows = [(name, _cents(sector_weight * pct / 100)) for name, pct in split[:-1]]
    rows.append((split[-1][0], sector_weight - sum((w for _, w in rows), _ZERO)))
    return rows


def _generate_exposures() -> list[SecurityExposure]:
    rng = random.Random(EXPOSURE_SEED)
    fund_ids = sorted(INITIAL_SECTOR_WEIGHTS)
    weights_by_quarter: list[dict[int, list[tuple[str, Decimal]]]] = []
    current = {sid: list(INITIAL_SECTOR_WEIGHTS[sid]) for sid in fund_ids}
    for index, _ in enumerate(EXPOSURE_DATES):
        if index > 0:
            for sid in fund_ids:
                previous = current[sid]
                others = [
                    (label, max(weight + Decimal(rng.randint(-10, 10)) / 100, _MIN_SECTOR_WEIGHT))
                    for label, weight in previous[1:]
                ]
                balancing = Decimal("100.00") - sum((w for _, w in others), _ZERO)
                current[sid] = [(previous[0][0], balancing), *others]
        weights_by_quarter.append({sid: list(current[sid]) for sid in fund_ids})

    exposures: list[SecurityExposure] = []
    for as_of, weights in zip(EXPOSURE_DATES, weights_by_quarter):
        for sid in fund_ids:
            sectors = weights[sid]
            rows = [("sector", label, weight) for label, weight in sectors]
            for label, weight in sectors:
                rows.extend(("industry", name, w) for name, w in _industry_rows(label, weight))
            for exposure_type, label, weight in rows:
                if weight <= _ZERO:
                    raise ValueError(f"Non-positive {exposure_type} weight {label} for {sid} on {as_of}")
                exposures.append(
                    SecurityExposure(len(exposures) + 1, sid, exposure_type, label, weight, as_of)
                )
    return exposures


# ---------------------------------------------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------------------------------------------


def generate_dataset() -> Dataset:
    """Build the full deterministic dataset (pure; no I/O)."""
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN
        closes = _generate_prices()
        simulation = _Simulation(closes)
        simulation.run()
        holdings = _build_holdings(simulation.books)
        exposures = _generate_exposures()

    accounts = tuple(
        Account(
            account_id=spec.account_id,
            client_id=spec.client_id,
            account_type=spec.account_type,
            account_name=spec.account_name,
            opened_date=spec.opened_date,
            cash_balance=simulation.books[spec.account_id].cash,
            objective=spec.objective,
        )
        for spec in ACCOUNT_SPECS
    )
    prices = tuple(
        SecurityPrice(sid, day, close) for (sid, day), close in sorted(closes.items())
    )
    snapshots = tuple(sorted(simulation.snapshots, key=lambda s: (s.account_id, s.snapshot_date)))
    return Dataset(
        advisors=ADVISORS,
        clients=CLIENTS,
        accounts=accounts,
        asset_classes=ASSET_CLASSES,
        securities=SECURITIES,
        security_exposures=tuple(exposures),
        security_prices=prices,
        holdings=tuple(holdings),
        transactions=tuple(simulation.transactions),
        portfolio_snapshots=snapshots,
    )


@dataclass(frozen=True)
class ClientSummary:
    client: Client
    advisor: Advisor
    accounts: tuple[Account, ...]


@dataclass(frozen=True)
class SeedSummary:
    """Counts, ranges, and names for the CLI `seed` command."""

    advisors: tuple[Advisor, ...]
    clients: tuple[ClientSummary, ...]
    securities: tuple[tuple[Security, str], ...]  # (security, asset class name)
    price_count: int
    price_first_date: date
    price_last_date: date
    snapshot_count: int
    snapshot_month_count: int
    snapshot_first_date: date
    snapshot_last_date: date
    holding_count: int
    exposure_count: int
    exposure_as_of_dates: tuple[date, ...]
    txn_counts_by_type: tuple[tuple[str, int], ...]  # in TXN_TYPES order
    txn_first_date: date
    txn_last_date: date


def summarize(dataset: Dataset) -> SeedSummary:
    advisors_by_id = {a.advisor_id: a for a in dataset.advisors}
    class_names = {c.asset_class_id: c.name for c in dataset.asset_classes}
    clients = tuple(
        ClientSummary(
            client=client,
            advisor=advisors_by_id[client.advisor_id],
            accounts=tuple(a for a in dataset.accounts if a.client_id == client.client_id),
        )
        for client in dataset.clients
    )
    price_dates = [p.price_date for p in dataset.security_prices]
    snapshot_dates = [s.snapshot_date for s in dataset.portfolio_snapshots]
    txn_dates = [t.txn_date for t in dataset.transactions]
    counts = {txn_type: 0 for txn_type in TXN_TYPES}
    for txn in dataset.transactions:
        counts[txn.txn_type] += 1
    return SeedSummary(
        advisors=dataset.advisors,
        clients=clients,
        securities=tuple((s, class_names[s.asset_class_id]) for s in dataset.securities),
        price_count=len(dataset.security_prices),
        price_first_date=min(price_dates),
        price_last_date=max(price_dates),
        snapshot_count=len(dataset.portfolio_snapshots),
        snapshot_month_count=len({(d.year, d.month) for d in snapshot_dates}),
        snapshot_first_date=min(snapshot_dates),
        snapshot_last_date=max(snapshot_dates),
        holding_count=len(dataset.holdings),
        exposure_count=len(dataset.security_exposures),
        exposure_as_of_dates=tuple(sorted({e.as_of_date for e in dataset.security_exposures})),
        txn_counts_by_type=tuple(counts.items()),
        txn_first_date=min(txn_dates),
        txn_last_date=max(txn_dates),
    )
