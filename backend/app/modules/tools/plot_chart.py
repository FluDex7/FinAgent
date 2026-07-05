from dataclasses import dataclass
from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# Shared across the app's charts (light and dark) — see frontend design spec §1.
CHART_PALETTE = ["#2b8fef", "#22b8a6", "#f0a94e", "#ee7d8c", "#94a3b8"]

ChartKind = Literal["bars", "line", "donut"]


class PlotChartInput(BaseModel):
    kind: ChartKind = Field(description="Тип графика: bars, line или donut")
    data: list[dict] = Field(
        description="Агрегированные точки вида [{'label': str, 'value': число}, ...]"
    )


@dataclass
class ChartPoint:
    label: str
    value: float


def build_chart_spec(kind: ChartKind, data: list[dict]) -> dict:
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
    """Строит спецификацию графика (bars/line/donut) для отображения в чате агента."""
    return build_chart_spec(kind, data)
