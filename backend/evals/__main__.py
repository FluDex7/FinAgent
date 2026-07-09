"""Runs the golden dataset through the real agent and scores it.

    uv run python -m evals [--only substr] [--judge-model NAME] [--skip-judge]

Needs a working LLM (the same .env the app uses). Everything is sandboxed:
fixtures go to a temp dir, all DB writes happen inside one transaction that
is rolled back at the end. Results are printed and logged to MLflow
(experiment «finagent-evals»), so quality is comparable across commits.
"""

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from dataclasses import asdict

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.modules.agent.service import AgentService
from app.shared.llm import get_chat_model
from evals.dataset import GOLDEN_CASES
from evals.runner import run_case, seed_fixtures
from evals.scoring import Scores, aggregate, build_judge, deterministic_scores, ragas_scores


def _git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def _print_report(results: dict[str, dict], aggregated: dict[str, float]) -> None:
    print()
    for case_id, entry in results.items():
        scores: Scores = entry["scores"]
        shown = ", ".join(
            f"{name}={value:.2f}" for name, value in sorted(scores.items()) if value is not None
        )
        flag = "✓" if all(v is None or v >= 0.5 for v in scores.values()) else "✗"
        print(f"  {flag} {case_id}: {shown}")
    print("\nАгрегаты по датасету:")
    for name, value in aggregated.items():
        print(f"  {name}: {value:.3f}")


def _log_to_mlflow(
    settings: Settings, args: argparse.Namespace, results: dict, aggregated: dict[str, float]
) -> None:
    import mlflow

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment("finagent-evals")
    with mlflow.start_run(run_name=f"evals-{_git_sha()}"):
        mlflow.log_params(
            {
                "llm_provider": settings.llm_provider,
                "model": settings.openai_model
                if settings.llm_provider == "openai"
                else settings.ollama_model,
                "judge_model": args.judge_model or "same-as-agent",
                "agent_self_check": settings.agent_self_check,
                "cases": len(results),
                "git_sha": _git_sha(),
            }
        )
        mlflow.log_metrics(aggregated)
        mlflow.log_text(json.dumps(results, ensure_ascii=False, indent=2), "results.json")
    print(f"\nЗалогировано в MLflow: {settings.mlflow_tracking_uri} → finagent-evals")


async def main() -> int:
    parser = argparse.ArgumentParser(prog="evals")
    parser.add_argument("--only", help="run only cases whose id contains this substring")
    parser.add_argument(
        "--judge-model",
        help="model name for the Ragas judge (default: the agent's own model)",
    )
    parser.add_argument(
        "--skip-judge",
        action="store_true",
        help="deterministic checks only — no Ragas LLM-judge calls",
    )
    args = parser.parse_args()

    cases = [c for c in GOLDEN_CASES if not args.only or args.only in c.id]
    if not cases:
        print(f"Нет кейсов с id, содержащим «{args.only}».")
        return 2

    with tempfile.TemporaryDirectory(prefix="finagent-evals-") as tmp_dir:
        settings = Settings(statements_dir=tmp_dir)
        if settings.llm_provider == "openai" and not settings.openai_api_key:
            print("OPENAI_API_KEY не задан — evals гоняют реального агента, нужен LLM.")
            return 2

        judge = None
        if not args.skip_judge:
            judge_settings = settings
            if args.judge_model:
                judge_settings = settings.model_copy(
                    update={"openai_model": args.judge_model, "ollama_model": args.judge_model}
                )
            judge = build_judge(get_chat_model(judge_settings))

        engine = create_async_engine(settings.database_url)
        results: dict[str, dict] = {}
        try:
            async with engine.connect() as conn:
                transaction = await conn.begin()
                maker = async_sessionmaker(bind=conn, expire_on_commit=False)
                session = maker()
                try:
                    service = AgentService(session, settings)
                    await seed_fixtures(service.statements)
                    print(f"Фикстуры загружены, кейсов: {len(cases)}")

                    for case in cases:
                        print(f"→ {case.id}: {case.question}")
                        trace = await run_case(service, case)
                        scores = deterministic_scores(case, trace)
                        if judge is not None:
                            scores |= await ragas_scores(case, trace, judge)
                        if trace.error:
                            print(f"  ! ошибка агента: {trace.error}")
                        results[case.id] = {
                            "question": case.question,
                            "reference": case.reference,
                            "trace": asdict(trace),
                            "scores": scores,
                        }
                finally:
                    await session.close()
                    # Nothing from the eval run may survive in the dev database.
                    await transaction.rollback()
        finally:
            await engine.dispose()

    aggregated = aggregate({cid: r["scores"] for cid, r in results.items()})
    _print_report(results, aggregated)
    _log_to_mlflow(settings, args, results, aggregated)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
