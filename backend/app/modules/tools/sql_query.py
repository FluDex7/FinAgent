import re
from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.core.database import Base
from app.core.exceptions import SqlValidationError
from app.modules.statements import (
    models as _statements_models,  # noqa: F401 (registers Base.metadata)
)
from app.modules.tools.sql_validation import validate_and_cap
from app.modules.transactions import models as _transactions_models  # noqa: F401
from app.modules.transactions.service import TransactionsService

WHITELISTED_TABLES = {"transactions", "categories", "merchants", "statements"}
DEFAULT_LIMIT = 500

SQL_PROMPT_TEMPLATE = """Ты — генератор PostgreSQL-запросов для личного финансового агента FinAgent.
Ответь ТОЛЬКО одним SQL SELECT-запросом, без пояснений и markdown-разметки.

Схема таблиц:
{schema}

statement_id — это колонка типа uuid. В неё можно подставлять ТОЛЬКО настоящий UUID, если он
явно дан тебе ниже перед вопросом. Даже если в вопросе пользователя упоминается имя файла —
это НЕ значение для statement_id, у тебя нет способа превратить имя файла в UUID. Если ниже
нет готового UUID, не добавляй условие на statement_id вовсе — выбери из всех доступных данных.

В transactions.amount расходы записаны ОТРИЦАТЕЛЬНЫМИ числами, а поступления (пополнения,
переводы на счёт, зарплата) — положительными. Для вопросов про траты/расходы/покупки всегда
добавляй фильтр amount < 0 (иначе в «расходы» попадут пополнения), а сумму показывай через
ABS(amount). Для вопросов про доходы/пополнения — amount > 0.

categories.is_system означает только «встроенная категория по умолчанию, а не созданная
пользователем» — это никак не связано с подписками/регулярными платежами, не используй это
поле как фильтр для таких вопросов. Определить подписку по одной SQL-выборке нельзя (нужна
GROUP BY/HAVING логика по повторяемости за несколько месяцев) — если вопрос про подписки или
регулярные платежи, откажись писать SQL и верни только слово SKIP.

{scope_hint}Вопрос пользователя: {question}
SQL:"""

_CODE_FENCE_RE = re.compile(r"^```(?:sql)?|```$", re.IGNORECASE | re.MULTILINE)


def describe_schema(whitelist: set[str]) -> str:
    lines = []
    for table in Base.metadata.sorted_tables:
        if table.name not in whitelist:
            continue
        columns = ", ".join(f"{c.name} {c.type}" for c in table.columns)
        lines.append(f"- {table.name}({columns})")
    return "\n".join(lines)


def _strip_code_fence(text: str) -> str:
    return _CODE_FENCE_RE.sub("", text).strip()


class SqlQueryInput(BaseModel):
    question: str = Field(description="Вопрос пользователя на естественном языке о его тратах")
    statement_ids: list[str] | None = Field(
        default=None, description="UUID выписок, к которым нужно ограничить запрос (опционально)"
    )


@dataclass
class SqlQueryOutcome:
    sql: str
    rows: list[dict]


async def generate_sql(
    chat_model: BaseChatModel, question: str, statement_ids: list[str] | None
) -> str:
    scope_hint = ""
    if statement_ids:
        ids = ", ".join(f"'{sid}'" for sid in statement_ids)
        scope_hint = f"Ограничь выборку условием transactions.statement_id IN ({ids})\n"

    prompt = SQL_PROMPT_TEMPLATE.format(
        schema=describe_schema(WHITELISTED_TABLES), scope_hint=scope_hint, question=question
    )
    response = await chat_model.ainvoke(prompt)
    content = response.content if isinstance(response.content, str) else str(response.content)
    return _strip_code_fence(content)


async def run_sql_query(
    *,
    transactions_service: TransactionsService,
    chat_model: BaseChatModel,
    question: str,
    statement_ids: list[str] | None = None,
) -> SqlQueryOutcome:
    raw_sql = await generate_sql(chat_model, question, statement_ids)
    if raw_sql.strip().upper().startswith("SKIP"):
        raise SqlValidationError(
            "Этот вопрос нельзя ответить одним SQL-запросом (например, про подписки/"
            "регулярные платежи — используй find_subscriptions)."
        )
    safe_sql = validate_and_cap(raw_sql, whitelist=WHITELISTED_TABLES, default_limit=DEFAULT_LIMIT)
    rows = await transactions_service.run_validated_sql(safe_sql)
    return SqlQueryOutcome(sql=safe_sql, rows=rows)


def build_sql_query_tool(
    transactions_service: TransactionsService, chat_model: BaseChatModel
) -> StructuredTool:
    """Factory, not a module-level @tool: sql_query needs a request-scoped DB session."""

    async def _run(question: str, statement_ids: list[str] | None = None) -> dict:
        outcome = await run_sql_query(
            transactions_service=transactions_service,
            chat_model=chat_model,
            question=question,
            statement_ids=statement_ids,
        )
        return {"sql": outcome.sql, "rows": outcome.rows}

    return StructuredTool.from_function(
        coroutine=_run,
        name="sql_query",
        description=(
            "Выполняет read-only аналитический SQL-запрос к транзакциям пользователя по вопросу "
            "на естественном языке. Возвращает сгенерированный SQL и строки результата."
        ),
        args_schema=SqlQueryInput,
    )
