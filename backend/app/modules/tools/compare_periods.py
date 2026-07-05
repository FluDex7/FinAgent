import uuid
from dataclasses import dataclass
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from app.modules.transactions.service import TransactionsService


class ComparePeriodsInput(BaseModel):
    period_a_statement_ids: list[str] = Field(
        description="UUID выписок первого (базового) периода"
    )
    period_b_statement_ids: list[str] = Field(
        description="UUID выписок второго периода — с чем сравниваем период A"
    )


@dataclass
class CategoryDelta:
    category: str
    period_a: float
    period_b: float
    delta: float
    growth_percent: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category,
            "periodA": self.period_a,
            "periodB": self.period_b,
            "delta": self.delta,
            "growthPercent": self.growth_percent,
        }


async def compare_periods(
    transactions_service: TransactionsService,
    period_a_statement_ids: list[str],
    period_b_statement_ids: list[str],
) -> dict[str, Any]:
    """Compares spending by category between two sets of statements.

    Only expense rows (negative amount) count towards the totals — this
    tool answers "where did I spend more", not net cash flow.
    """
    a_ids = [uuid.UUID(s) for s in period_a_statement_ids]
    b_ids = [uuid.UUID(s) for s in period_b_statement_ids]

    a_sums = await transactions_service.sum_by_category(a_ids, expenses_only=True)
    b_sums = await transactions_service.sum_by_category(b_ids, expenses_only=True)
    categories = await transactions_service.list_categories()
    names: dict[uuid.UUID | None, str] = {c.id: c.name for c in categories}

    deltas: list[CategoryDelta] = []
    for category_id in set(a_sums) | set(b_sums):
        a_total = abs(float(a_sums.get(category_id) or 0))
        b_total = abs(float(b_sums.get(category_id) or 0))
        delta = b_total - a_total
        growth_percent = round(delta / a_total * 100, 1) if a_total else None
        deltas.append(
            CategoryDelta(
                category=names.get(category_id, "Без категории"),
                period_a=a_total,
                period_b=b_total,
                delta=delta,
                growth_percent=growth_percent,
            )
        )

    deltas.sort(key=lambda d: abs(d.delta), reverse=True)
    total_a = sum(d.period_a for d in deltas)
    total_b = sum(d.period_b for d in deltas)

    return {
        "totalA": total_a,
        "totalB": total_b,
        "totalDelta": total_b - total_a,
        "categories": [d.to_dict() for d in deltas],
        "biggestDriver": deltas[0].category if deltas else None,
    }


def build_compare_periods_tool(transactions_service: TransactionsService) -> StructuredTool:
    async def _run(
        period_a_statement_ids: list[str], period_b_statement_ids: list[str]
    ) -> dict[str, Any]:
        return await compare_periods(
            transactions_service, period_a_statement_ids, period_b_statement_ids
        )

    return StructuredTool.from_function(
        coroutine=_run,
        name="compare_periods",
        description=(
            "Сравнивает траты по категориям между двумя периодами (списками id выписок): "
            "суммы, дельты, рост в % и главный драйвер изменения. Не формулирует вывод — "
            "это делает сама модель на основе данных."
        ),
        args_schema=ComparePeriodsInput,
    )
