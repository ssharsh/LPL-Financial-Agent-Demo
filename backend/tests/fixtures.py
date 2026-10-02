"""Builders for small hand-made Datasets used by tests.

Performance fixtures F1-F6 (plan.md section 5): one advisor, one client (client 1, advisor 1), the needed
accounts, month-end snapshots, and deposit/withdrawal transactions. No prices are needed for performance.
"""

from datetime import date
from decimal import Decimal

from advisor.data.models import Account, Advisor, Client, Dataset, PortfolioSnapshot, Transaction

FIXTURE_CLIENT_ID = 1
ACCT_X = 901
ACCT_Y = 902


def empty_dataset() -> Dataset:
    """A Dataset with no rows in any collection."""
    return Dataset(
        advisors=(),
        clients=(),
        accounts=(),
        asset_classes=(),
        securities=(),
        security_exposures=(),
        security_prices=(),
        holdings=(),
        transactions=(),
        portfolio_snapshots=(),
    )


def flow_dataset(
    account_ids: tuple[int, ...],
    snapshots: list[tuple[int, str, str]],
    flows: list[tuple[int, str, str, str]],
) -> Dataset:
    """One advisor, one client owning `account_ids`, snapshots (account, date, value), flows
    (account, txn_type, date, amount). transaction_id = 1..N in the given order."""
    return Dataset(
        advisors=(Advisor(1, "Test", "Advisor", "advisor@example.com"),),
        clients=(
            Client(FIXTURE_CLIENT_ID, 1, "Test", "Client", "client@example.com", None, None, None),
        ),
        accounts=tuple(
            Account(a, FIXTURE_CLIENT_ID, "brokerage", f"Account {a}", date(2025, 1, 2), Decimal("0.00"), None)
            for a in account_ids
        ),
        asset_classes=(),
        securities=(),
        security_exposures=(),
        security_prices=(),
        holdings=(),
        transactions=tuple(
            Transaction(i, a, None, t, None, None, Decimal(amount), date.fromisoformat(day))
            for i, (a, t, day, amount) in enumerate(flows, start=1)
        ),
        portfolio_snapshots=tuple(
            PortfolioSnapshot(a, date.fromisoformat(day), Decimal(value), None) for a, day, value in snapshots
        ),
    )


def f1_dataset() -> Dataset:
    """F1 mid-month deposit: 2025-03-31 10000.00; deposit 1000.00 on 2025-04-11; 2025-04-30 11500.00."""
    return flow_dataset(
        (ACCT_X,),
        [(ACCT_X, "2025-03-31", "10000.00"), (ACCT_X, "2025-04-30", "11500.00")],
        [(ACCT_X, "deposit", "2025-04-11", "1000.00")],
    )


def f2_dataset() -> Dataset:
    """F2 withdrawal: 2025-04-30 11500.00; withdrawal 2000.00 on 2025-05-21; 2025-05-31 9800.00."""
    return flow_dataset(
        (ACCT_X,),
        [(ACCT_X, "2025-04-30", "11500.00"), (ACCT_X, "2025-05-31", "9800.00")],
        [(ACCT_X, "withdrawal", "2025-05-21", "2000.00")],
    )


def f1_f2_dataset() -> Dataset:
    """F1 followed by F2 in one account (window 2025-04..2025-05)."""
    return flow_dataset(
        (ACCT_X,),
        [
            (ACCT_X, "2025-03-31", "10000.00"),
            (ACCT_X, "2025-04-30", "11500.00"),
            (ACCT_X, "2025-05-31", "9800.00"),
        ],
        [(ACCT_X, "deposit", "2025-04-11", "1000.00"), (ACCT_X, "withdrawal", "2025-05-21", "2000.00")],
    )


def f3_dataset() -> Dataset:
    """F3 null denominator: 2025-06-30 0.00; deposit 5000.00 on 2025-07-31 (w=0); 2025-07-31 5000.00;
    2025-08-31 5100.00."""
    return flow_dataset(
        (ACCT_X,),
        [
            (ACCT_X, "2025-06-30", "0.00"),
            (ACCT_X, "2025-07-31", "5000.00"),
            (ACCT_X, "2025-08-31", "5100.00"),
        ],
        [(ACCT_X, "deposit", "2025-07-31", "5000.00")],
    )


def f4_dataset() -> Dataset:
    """F4 coverage: snapshots 2025-03-31..2025-08-31 with 2025-06-30 missing (a gap); no flows."""
    return flow_dataset(
        (ACCT_X,),
        [
            (ACCT_X, "2025-03-31", "1000.00"),
            (ACCT_X, "2025-04-30", "1010.00"),
            (ACCT_X, "2025-05-31", "1020.00"),
            (ACCT_X, "2025-07-31", "1030.00"),
            (ACCT_X, "2025-08-31", "1040.00"),
        ],
        [],
    )


def f5_dataset() -> Dataset:
    """F5 portfolio level: account X 10000.00 -> 11000.00, account Y 1000.00 -> 900.00 over 2025-04; no flows."""
    return flow_dataset(
        (ACCT_X, ACCT_Y),
        [
            (ACCT_X, "2025-03-31", "10000.00"),
            (ACCT_X, "2025-04-30", "11000.00"),
            (ACCT_Y, "2025-03-31", "1000.00"),
            (ACCT_Y, "2025-04-30", "900.00"),
        ],
        [],
    )


def f6_dataset() -> Dataset:
    """F6 two flows: 2025-05-31 20000.00; deposit 3000.00 on 2025-06-06; withdrawal 500.00 on 2025-06-26;
    2025-06-30 23100.00."""
    return flow_dataset(
        (ACCT_X,),
        [(ACCT_X, "2025-05-31", "20000.00"), (ACCT_X, "2025-06-30", "23100.00")],
        [(ACCT_X, "deposit", "2025-06-06", "3000.00"), (ACCT_X, "withdrawal", "2025-06-26", "500.00")],
    )


def snapshot_values(dataset: Dataset) -> dict[tuple[int, date], Decimal]:
    return {(s.account_id, s.snapshot_date): s.total_value for s in dataset.portfolio_snapshots}
