import logging

from app.core.health import CheckResult


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def format_banner(results: list[CheckResult], ui_url: str) -> str:
    lines = ["FinAgent — проверка окружения…"]
    for r in results:
        mark = "✓" if r.ok else "✗"
        lines.append(f"  {mark} {r.name:<20} — {r.detail}")
        if not r.ok and r.hint:
            lines.append(f"      → {r.hint}")

    if all(r.ok for r in results):
        lines.append(f"▶ Готово. UI: {ui_url}")
    else:
        lines.append("▶ Есть проблемы окружения — сервис запущен, но часть функций не работает.")

    return "\n".join(lines)


def print_health_banner(results: list[CheckResult], ui_url: str) -> None:
    print(format_banner(results, ui_url))
