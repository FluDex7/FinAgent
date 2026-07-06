from dataclasses import dataclass
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Shared across the app's charts (light and dark) — see frontend design spec §1.
CHART_PALETTE = ["#2b8fef", "#22b8a6", "#f0a94e", "#ee7d8c", "#94a3b8"]

ChartKind = Literal["bars", "line", "donut", "metrics", "table"]


class PlotChartInput(BaseModel):
    kind: ChartKind = Field(
        description=(
            "Тип блока: bars/line/donut — числовой график; metrics — 2-4 сводные карточки "
            "(например, «Всего расходов», «Операций», «Средний чек»); table — произвольная "
            "таблица строк."
        )
    )
    data: list[dict] = Field(
        description=(
            "Для bars/line/donut: [{'label': str, 'value': число}, ...], передавай "
            "положительную величину (модуль суммы), даже если в БД расход хранится "
            "отрицательным — столбики должны расти вверх, знак уже понятен из контекста "
            "ответа. Отрицательные value допустимы только когда сам знак несёт смысл: "
            "например, дельта роста/падения по категориям между периодами. "
            "Для metrics: [{'label': str, 'value': str|число}, ...] — value можно передать "
            "уже отформатированной строкой (например, '119 400 ₽'). "
            "Для table: произвольный массив объектов с одинаковыми ключами — каждый ключ "
            "станет колонкой."
        )
    )


@dataclass
class ChartPoint:
    label: str
    value: float


def build_chart_spec(kind: ChartKind, data: list[dict]) -> dict:
    if kind in ("metrics", "table"):
        # Free-form rows — metrics values may be pre-formatted strings, table rows have
        # arbitrary columns — neither fits the label/value numeric point shape below.
        return {"kind": kind, "data": data}

    points = [ChartPoint(label=str(row["label"]), value=float(row["value"])) for row in data]

    if kind != "donut":
        return {"kind": kind, "data": [{"label": p.label, "value": p.value} for p in points]}

    total = sum(p.value for p in points) or 1
    series = [
        {
            "label": p.label,
            "value": p.value,
            "percent": round(p.value / total * 100, 1),
            "color": CHART_PALETTE[i % len(CHART_PALETTE)],
        }
        for i, p in enumerate(points)
    ]
    return {"kind": kind, "data": series}


@tool("plot_chart", args_schema=PlotChartInput)
def plot_chart(kind: ChartKind, data: list[dict]) -> dict:
    """Строит визуальный блок (bars/line/donut/metrics/table) для отображения в чате
    агента. Можно вызывать несколько раз за один ответ — например, metrics со сводкой,
    а затем donut/bars с разбивкой по категориям, для полного разбора трат."""
    return build_chart_spec(kind, data)
