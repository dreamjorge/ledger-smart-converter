import common_utils as cu


def test_parse_money_handles_common_formats():
    assert cu.parse_money("$1,234.56") == 1234.56
    assert cu.parse_money("-45.90") == -45.90
    assert cu.parse_money("1 500.00") == 1500.00
    assert cu.parse_money("abc") is None


def test_statement_period_uses_closing_day():
    assert cu.get_statement_period("2026-01-10", 15) == "2026-01"
    assert cu.get_statement_period("2026-01-16", 15) == "2026-02"
