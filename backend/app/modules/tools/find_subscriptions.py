import uuid

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.modules.transactions.service import TransactionsService


class FindSubscriptionsInput(BaseModel):
    statement_ids: list[str] | None = Field(
        default=None,
        description=(
            "Опционально: ограничить поиск конкретными выписками. По умолчанию не задавай — "
            "подписки ищутся по повторяемости в разных месяцах, поэтому им нужны все "
            "доступные данные, а не один файл."
        ),
    )


async def find_subscriptions(
    transactions_service: TransactionsService, statement_ids: list[str] | None = None
) -> list[dict]:
    ids = [uuid.UUID(s) for s in statement_ids] if statement_ids else None
    rows = await transactions_service.find_recurring_merchants(ids)
    return [
        {
            "merchant": r["merchant"],
            "occurrences": r["occurrences"],
            "distinctMonths": r["distinct_months"],
            "avgAmount": float(r["avg_amount"]),
            "minAmount": float(r["min_amount"]),
            "maxAmount": float(r["max_amount"]),
            "lastDate": r["last_date"].isoformat(),
        }
        for r in rows
    ]


def build_find_subscriptions_tool(transactions_service: TransactionsService) -> StructuredTool:
    async def _run(statement_ids: list[str] | None = None) -> list[dict]:
        return await find_subscriptions(transactions_service, statement_ids)

    return StructuredTool.from_function(
        coroutine=_run,
        name="find_subscriptions",
        description=(
            "Находит подписки и регулярные платежи по фактической повторяемости: продавец, "
            "списывающий примерно одну и ту же сумму в нескольких разных месяцах. Это "
            "единственный надёжный сигнал подписки — в БД нет ни поля 'это подписка', ни "
            "признака периодичности где-либо ещё, поэтому для вопросов о подписках/регулярных "
            "платежах используй именно этот инструмент, а не sql_query (там неоткуда взять "
            "такую логику одним запросом)."
        ),
        args_schema=FindSubscriptionsInput,
    )
