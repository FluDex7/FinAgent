import sqlglot
from sqlglot import exp

from app.core.exceptions import SqlValidationError

DIALECT = "postgres"

_FORBIDDEN_EXPRESSIONS = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Alter, exp.Create)


def validate_and_cap(raw_sql: str, *, whitelist: set[str], default_limit: int) -> str:
    """Enforces: single SELECT, whitelisted tables only, no writes, a LIMIT is always present."""
    sql = raw_sql.strip().strip(";").strip()
    if not sql:
        raise SqlValidationError("LLM вернул пустой SQL-запрос.")

    try:
        statements = [s for s in sqlglot.parse(sql, dialect=DIALECT) if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise SqlValidationError(f"Не удалось разобрать сгенерированный SQL: {exc}") from exc

    if len(statements) != 1:
        raise SqlValidationError("Допускается ровно один SQL-запрос за раз.")

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise SqlValidationError("Разрешены только запросы SELECT.")

    for forbidden in _FORBIDDEN_EXPRESSIONS:
        if statement.find(forbidden):
            raise SqlValidationError("Изменяющие данные операции запрещены — только чтение.")

    tables = {table.name.lower() for table in statement.find_all(exp.Table)}
    unknown = tables - whitelist
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SqlValidationError(f"Запрос обращается к недопустимым таблицам: {names}")

    if statement.args.get("limit") is None:
        statement = statement.limit(default_limit)

    return statement.sql(dialect=DIALECT)
