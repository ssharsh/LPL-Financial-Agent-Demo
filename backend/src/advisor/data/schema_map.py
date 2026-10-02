"""The only module that spells the teammate's table and column names (chatbot-schema-v2.sql).

Domain field -> database column for every entity. Enum values are currently identical in the domain and the
database (see data/models.py); Phase 3 adds a contract check against the live schema.
"""

from collections.abc import Mapping
from dataclasses import dataclass, fields

from advisor.data.models import (
    Account,
    Advisor,
    AssetClass,
    Client,
    Holding,
    PortfolioSnapshot,
    Security,
    SecurityExposure,
    SecurityPrice,
    Transaction,
)


@dataclass(frozen=True)
class EntityMap:
    table: str
    columns: Mapping[str, str]  # domain field -> teammate column


def _identity(model: type, **renames: str) -> dict[str, str]:
    """Map every dataclass field to the same-named column, except the given renames."""
    return {f.name: renames.get(f.name, f.name) for f in fields(model)}


ENTITY_MAPS: dict[str, EntityMap] = {
    "advisor": EntityMap("advisors", _identity(Advisor)),
    "client": EntityMap("customers", _identity(Client, client_id="customer_id")),
    "account": EntityMap("accounts", _identity(Account, client_id="customer_id")),
    "asset_class": EntityMap("asset_classes", _identity(AssetClass)),
    "security": EntityMap("securities", _identity(Security)),
    "security_exposure": EntityMap("security_exposures", _identity(SecurityExposure)),
    "security_price": EntityMap("security_prices", _identity(SecurityPrice)),
    "holding": EntityMap("holdings", _identity(Holding)),
    "transaction": EntityMap("transactions", _identity(Transaction)),
    "portfolio_snapshot": EntityMap("portfolio_snapshots", _identity(PortfolioSnapshot)),
    # Phase 5 (audit index); no domain model yet.
    "log_export": EntityMap(
        "chat_log_exports",
        {
            "log_export_id": "log_id",
            "chat_session_id": "session_id",
            "s3_key": "s3_key",
            "content_hash": "content_hash",
            "exported_at": "exported_at",
        },
    ),
}

MODEL_FOR_ENTITY: dict[str, type] = {
    "advisor": Advisor,
    "client": Client,
    "account": Account,
    "asset_class": AssetClass,
    "security": Security,
    "security_exposure": SecurityExposure,
    "security_price": SecurityPrice,
    "holding": Holding,
    "transaction": Transaction,
    "portfolio_snapshot": PortfolioSnapshot,
}

# Every table in chatbot-schema-v2.sql, mapped or not.
TEAMMATE_TABLES: frozenset[str] = frozenset(
    {
        "advisors",
        "customers",
        "accounts",
        "asset_classes",
        "securities",
        "security_exposures",
        "security_prices",
        "holdings",
        "transactions",
        "portfolio_snapshots",
        "benchmarks",
        "benchmark_values",
        "target_allocations",
        "investment_rationales",
        "glossary_terms",
        "research_notes",
        "chat_sessions",
        "chat_messages",
        "message_citations",
        "message_view_context",
        "message_reviews",
        "followup_actions",
        "chat_log_exports",
    }
)

# Names that must not appear outside advisor/data/ (enforced by tests/test_schema_map.py).
TEAMMATE_ONLY_NAMES: frozenset[str] = TEAMMATE_TABLES | {"customer_id"}
