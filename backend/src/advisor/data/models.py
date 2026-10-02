"""Domain records.

Field names equal the teammate's column names (chatbot-schema-v2.sql) except `client_id`, which is
`customers.customer_id` in the database. Field order follows the v2 column order. Literal values equal the
v2 CHECK constraints.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal, get_args

AccountType = Literal["brokerage", "traditional_ira", "roth_ira", "401k", "529", "trust"]
SecurityType = Literal["stock", "etf", "mutual_fund", "bond", "cash_equiv"]
RiskTolerance = Literal["conservative", "moderate", "aggressive"]
FinancialLiteracy = Literal["beginner", "intermediate", "advanced"]
# v2 removed 'rebalance'; rebalances are ordinary buy/sell pairs.
TxnType = Literal["buy", "sell", "dividend", "deposit", "withdrawal", "fee"]
ExposureType = Literal["sector", "region", "top_holding", "credit_quality", "industry"]

ACCOUNT_TYPES: tuple[str, ...] = get_args(AccountType)
SECURITY_TYPES: tuple[str, ...] = get_args(SecurityType)
RISK_TOLERANCES: tuple[str, ...] = get_args(RiskTolerance)
FINANCIAL_LITERACY_LEVELS: tuple[str, ...] = get_args(FinancialLiteracy)
TXN_TYPES: tuple[str, ...] = get_args(TxnType)
EXPOSURE_TYPES: tuple[str, ...] = get_args(ExposureType)


@dataclass(frozen=True, slots=True)
class Advisor:
    advisor_id: int
    first_name: str
    last_name: str
    email: str


@dataclass(frozen=True, slots=True)
class Client:
    client_id: int
    advisor_id: int
    first_name: str
    last_name: str
    email: str
    risk_tolerance: RiskTolerance | None
    financial_literacy: FinancialLiteracy | None
    client_since: date | None


@dataclass(frozen=True, slots=True)
class Account:
    account_id: int
    client_id: int
    account_type: AccountType
    account_name: str | None
    opened_date: date
    cash_balance: Decimal
    objective: str | None


@dataclass(frozen=True, slots=True)
class AssetClass:
    asset_class_id: int
    name: str
    description: str | None
    role_in_portfolio: str | None
    color_hex: str | None


@dataclass(frozen=True, slots=True)
class Security:
    security_id: int
    ticker: str
    name: str
    security_type: SecurityType
    asset_class_id: int
    sector: str | None
    region: str | None
    expense_ratio: Decimal | None
    dividend_yield: Decimal | None
    risk_rating: int | None
    description: str | None


@dataclass(frozen=True, slots=True)
class SecurityExposure:
    exposure_id: int
    security_id: int
    exposure_type: ExposureType
    label: str
    weight_pct: Decimal
    as_of_date: date


@dataclass(frozen=True, slots=True)
class SecurityPrice:
    security_id: int
    price_date: date
    close_price: Decimal


@dataclass(frozen=True, slots=True)
class Holding:
    holding_id: int
    account_id: int
    security_id: int
    quantity: Decimal
    avg_cost_basis: Decimal  # per share (documented in v2)
    first_purchased: date | None


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    account_id: int
    snapshot_date: date
    total_value: Decimal
    # PROVISIONAL (pending DB teammate): total_contributions semantics are undefined in v2 (P6); the seed
    # leaves it None and no tool reads it.
    total_contributions: Decimal | None


@dataclass(frozen=True, slots=True)
class Transaction:
    transaction_id: int
    account_id: int
    security_id: int | None
    txn_type: TxnType
    quantity: Decimal | None
    price: Decimal | None
    amount: Decimal
    txn_date: date


@dataclass(frozen=True, slots=True)
class IdentityRecord:
    client_id: int
    advisor_id: int


@dataclass(frozen=True, slots=True)
class Dataset:
    advisors: tuple[Advisor, ...]
    clients: tuple[Client, ...]
    accounts: tuple[Account, ...]
    asset_classes: tuple[AssetClass, ...]
    securities: tuple[Security, ...]
    security_exposures: tuple[SecurityExposure, ...]
    security_prices: tuple[SecurityPrice, ...]
    holdings: tuple[Holding, ...]
    transactions: tuple[Transaction, ...]
    portfolio_snapshots: tuple[PortfolioSnapshot, ...]
