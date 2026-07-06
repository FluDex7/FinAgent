from app.modules.tools.plot_chart import CHART_PALETTE, build_chart_spec


def test_bars_pass_through_without_colors():
    data = [{"label": "Март", "value": 1000}, {"label": "Апрель", "value": 2000}]
    spec = build_chart_spec("bars", data)
    assert spec["kind"] == "bars"
    assert spec["data"] == [
        {"label": "Март", "value": 1000.0},
        {"label": "Апрель", "value": 2000.0},
    ]


def test_donut_computes_percent_and_cycles_colors():
    data = [{"label": "Продукты", "value": 60}, {"label": "Транспорт", "value": 40}]
    spec = build_chart_spec("donut", data)
    assert spec["kind"] == "donut"
    assert spec["data"][0]["percent"] == 60.0
    assert spec["data"][1]["percent"] == 40.0
    assert spec["data"][0]["color"] == CHART_PALETTE[0]
    assert spec["data"][1]["color"] == CHART_PALETTE[1]


def test_donut_handles_zero_total_without_division_error():
    spec = build_chart_spec("donut", [{"label": "Пусто", "value": 0}])
    assert spec["data"][0]["percent"] == 0.0


def test_donut_cycles_palette_beyond_its_length():
    data = [{"label": str(i), "value": 1} for i in range(len(CHART_PALETTE) + 2)]
    spec = build_chart_spec("donut", data)
    assert spec["data"][len(CHART_PALETTE)]["color"] == CHART_PALETTE[0]


def test_metrics_passes_rows_through_unmodified():
    data = [{"label": "Всего расходов", "value": "119 400 ₽"}, {"label": "Операций", "value": 47}]
    spec = build_chart_spec("metrics", data)
    assert spec == {"kind": "metrics", "data": data}


def test_table_passes_arbitrary_rows_through_unmodified():
    data = [{"date": "2025-01-14", "merchant": "PYATEROCHKA", "amount": -540.0}]
    spec = build_chart_spec("table", data)
    assert spec == {"kind": "table", "data": data}
