"""Hand-computed Modified Dietz fixtures (plan.md section 5). Expected values are worked out by hand, not
taken from the implementation."""

from datetime import date
from fractions import Fraction

import pytest

from advisor.calc.performance import RETURN_LABEL, cents, compute_performance, percent_2dp
from advisor.errors import DataUnavailableError, ToolArgumentError
from fixtures import (
    ACCT_X,
    ACCT_Y,
    f1_dataset,
    f1_f2_dataset,
    f2_dataset,
    f3_dataset,
    f4_dataset,
    f5_dataset,
    f6_dataset,
    snapshot_values,
)

TOLERANCE = Fraction(1, 10**20)


def run(dataset, start, end, accounts=(ACCT_X,)):
    return compute_performance(snapshot_values(dataset), dataset.transactions, start, end, accounts)


def assert_close(value, expected: Fraction):
    assert abs(Fraction(value) - expected) < TOLERANCE


def test_label_is_exact():
    assert RETURN_LABEL == "time-weighted return (monthly Modified Dietz, linked)"


def test_f1_mid_month_deposit():
    result = run(f1_dataset(), (2025, 4), (2025, 4))
    (month,) = result.months
    assert_close(month.monthly_return, Fraction(15, 319))
    assert str(percent_2dp(month.monthly_return)) == "4.70"
    assert str(cents(month.weighted_flow)) == "633.33"
    assert str(cents(month.denominator)) == "10633.33"
    assert str(cents(result.investment_gain)) == "500.00"
    assert str(percent_2dp(result.twr)) == "4.70"


def test_f2_withdrawal():
    result = run(f2_dataset(), (2025, 5), (2025, 5))
    (month,) = result.months
    assert_close(month.monthly_return, Fraction(93, 3365))
    assert str(percent_2dp(month.monthly_return)) == "2.76"
    assert str(cents(month.weighted_flow)) == "-645.16"
    assert str(cents(month.denominator)) == "10854.84"


def test_f1_f2_linked():
    result = run(f1_f2_dataset(), (2025, 4), (2025, 5))
    assert_close(result.twr, Fraction(81537, 1073435))
    assert str(percent_2dp(result.twr)) == "7.60"
    assert str(cents(result.start_value)) == "10000.00"
    assert str(cents(result.end_value)) == "9800.00"
    assert str(cents(result.net_flows)) == "-1000.00"
    assert str(cents(result.investment_gain)) == "800.00"
    assert result.start_value_date == date(2025, 3, 31)
    assert result.end_value_date == date(2025, 5, 31)
    assert result.flow_transaction_ids == (1, 2)


def test_f6_two_flows():
    result = run(f6_dataset(), (2025, 6), (2025, 6))
    (month,) = result.months
    assert_close(month.monthly_return, Fraction(9, 335))
    assert str(percent_2dp(month.monthly_return)) == "2.69"
    assert str(cents(month.weighted_flow)) == "2333.33"


def test_f5_portfolio_level_not_average():
    result = run(f5_dataset(), (2025, 4), (2025, 4), accounts=(ACCT_X, ACCT_Y))
    assert_close(result.twr, Fraction(900, 11000))
    assert str(percent_2dp(result.twr)) == "8.18"


def test_f3_null_denominator():
    result = run(f3_dataset(), (2025, 7), (2025, 8))
    july, august = result.months
    assert july.monthly_return is None
    assert "2025-07" in july.reason
    assert august.reason is None
    assert str(percent_2dp(august.monthly_return)) == "2.00"
    assert result.twr is None
    assert "2025-07" in result.return_unavailable_reason
    assert "2025-08" not in result.return_unavailable_reason
    assert str(cents(result.start_value)) == "0.00"
    assert str(cents(result.end_value)) == "5100.00"
    assert str(cents(result.net_flows)) == "5000.00"
    assert str(cents(result.investment_gain)) == "100.00"


def test_f4_start_before_first_snapshot_names_earliest_valid_start():
    with pytest.raises(DataUnavailableError, match="2025-04"):
        run(f4_dataset(), (2025, 3), (2025, 4))


def test_f4_end_after_last_snapshot_names_latest_valid_end():
    with pytest.raises(DataUnavailableError, match="latest valid end month is 2025-08"):
        run(f4_dataset(), (2025, 8), (2025, 9))


def test_f4_gap_month_is_named():
    with pytest.raises(DataUnavailableError, match="2025-06-30"):
        run(f4_dataset(), (2025, 4), (2025, 8))


def test_f4_gap_at_start_is_named():
    with pytest.raises(DataUnavailableError, match="2025-06-30"):
        run(f4_dataset(), (2025, 7), (2025, 8))


def test_f4_start_after_end_is_argument_error():
    with pytest.raises(ToolArgumentError):
        run(f4_dataset(), (2025, 5), (2025, 4))


def test_f4_valid_window_inside_coverage_works():
    result = run(f4_dataset(), (2025, 4), (2025, 5))
    assert_close(result.twr, Fraction(1020, 1000) - 1)
