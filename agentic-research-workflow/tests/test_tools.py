from src.tools import date_parser


def test_date_parser_last_quarter_uses_real_month_end() -> None:
    result = date_parser("last quarter", reference_date="2025-04-15")

    assert result["ok"] is True
    assert result["normalized"]["start"] == "2025-01-01"
    assert result["normalized"]["end"] == "2025-03-31"
