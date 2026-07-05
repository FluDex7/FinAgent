import pytest

from app.core.exceptions import SqlValidationError
from app.modules.tools.sql_validation import validate_and_cap

WHITELIST = {"transactions", "categories", "merchants", "statements"}


def test_injects_limit_when_missing():
    sql = validate_and_cap(
        "SELECT category_id, SUM(amount) FROM transactions GROUP BY category_id",
        whitelist=WHITELIST,
        default_limit=500,
    )
    assert "LIMIT 500" in sql.upper()


def test_keeps_existing_limit():
    sql = validate_and_cap(
        "SELECT * FROM transactions LIMIT 10", whitelist=WHITELIST, default_limit=500
    )
    assert "LIMIT 10" in sql.upper()
    assert "LIMIT 500" not in sql.upper()


def test_rejects_non_select():
    with pytest.raises(SqlValidationError):
        validate_and_cap(
            "UPDATE transactions SET amount = 0", whitelist=WHITELIST, default_limit=500
        )


def test_rejects_drop():
    with pytest.raises(SqlValidationError):
        validate_and_cap("DROP TABLE transactions", whitelist=WHITELIST, default_limit=500)


def test_rejects_unknown_table():
    with pytest.raises(SqlValidationError) as exc_info:
        validate_and_cap(
            "SELECT * FROM pg_user", whitelist=WHITELIST, default_limit=500
        )
    assert "pg_user" in str(exc_info.value)


def test_rejects_multiple_statements():
    with pytest.raises(SqlValidationError):
        validate_and_cap(
            "SELECT * FROM transactions; DROP TABLE transactions;",
            whitelist=WHITELIST,
            default_limit=500,
        )


def test_rejects_empty_sql():
    with pytest.raises(SqlValidationError):
        validate_and_cap("   ", whitelist=WHITELIST, default_limit=500)


def test_rejects_unparseable_sql():
    with pytest.raises(SqlValidationError):
        validate_and_cap("SELEC * FROM transactions !!!", whitelist=WHITELIST, default_limit=500)


def test_allows_join_across_whitelisted_tables():
    sql = validate_and_cap(
        "SELECT t.id, c.name FROM transactions t JOIN categories c ON t.category_id = c.id",
        whitelist=WHITELIST,
        default_limit=500,
    )
    assert "LIMIT 500" in sql.upper()
