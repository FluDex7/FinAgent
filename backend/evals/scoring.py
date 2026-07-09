"""Per-case scoring: cheap deterministic checks + Ragas LLM-judge metrics.

Deterministic checks encode the failure modes this project actually hit in
live testing (wrong answer language, transfers passed off as spending is
covered by the judge via references, leaked SQL, markdown tables, missing
charts) — they cost nothing and never flake. The judge metrics (faithfulness,
factual correctness against the golden reference) need an LLM and measure
what regexes can't: whether the answer is true.
"""

import re
import warnings
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel

from evals.dataset import GoldenCase
from evals.runner import AgentTrace

# Scores are floats in [0, 1]; None means "not applicable to this case".
Scores = dict[str, float | None]

_SQL_RE = re.compile(r"\bSELECT\b.+?\bFROM\b", re.IGNORECASE | re.DOTALL)
_CYRILLIC_RE = re.compile(r"[а-яё]", re.IGNORECASE)
_LATIN_RE = re.compile(r"[a-z]", re.IGNORECASE)


def _language_ok(expected: str, answer: str) -> float | None:
    cyr = len(_CYRILLIC_RE.findall(answer))
    lat = len(_LATIN_RE.findall(answer))
    if cyr + lat == 0:
        return None
    ratio = cyr / (cyr + lat)
    # Data values (category/merchant names) legitimately stay untranslated,
    # so an English answer may contain some Cyrillic and vice versa.
    return float(ratio >= 0.5) if expected == "ru" else float(ratio < 0.5)


def deterministic_scores(case: GoldenCase, trace: AgentTrace) -> Scores:
    scores: Scores = {
        "tools_expected": (
            float(all(t in trace.tools for t in case.expected_tools))
            if case.expected_tools
            else None
        ),
        "tools_forbidden_absent": (
            float(not any(t in trace.tools for t in case.forbidden_tools))
            if case.forbidden_tools
            else None
        ),
        "language_match": _language_ok(case.language, trace.answer),
        "no_sql_leak": float(not _SQL_RE.search(trace.answer)),
        "no_markdown_table": float("|---" not in trace.answer),
        "chart_present": float(trace.has_chart) if case.expect_chart else None,
    }
    if trace.error is not None:
        scores["completed"] = 0.0
    else:
        scores["completed"] = float(bool(trace.answer.strip()))
    return scores


def build_judge(chat_model: BaseChatModel) -> Any:
    from ragas.llms import LangchainLLMWrapper

    return LangchainLLMWrapper(chat_model)


async def ragas_scores(case: GoldenCase, trace: AgentTrace, judge: Any) -> Scores:
    # ragas 0.4 warns that these class-based metrics move in 1.0 — the pin in
    # pyproject keeps us on 0.4, where they are the API that works with any
    # LangChain chat model (incl. Ollama) instead of requiring an OpenAI client.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from ragas.dataset_schema import SingleTurnSample
        from ragas.metrics import FactualCorrectness, Faithfulness

    scores: Scores = {"faithfulness": None, "factual_correctness": None}
    if trace.error is not None or not trace.answer.strip():
        return scores

    factual = FactualCorrectness(llm=judge)
    scores["factual_correctness"] = await factual.single_turn_ascore(
        SingleTurnSample(
            user_input=case.question, response=trace.answer, reference=case.reference
        )
    )

    # Faithfulness = "is the answer grounded in the tool outputs" — meaningless
    # for tool-free answers (refusals, disclaimers), so those are skipped.
    if trace.contexts:
        faithfulness = Faithfulness(llm=judge)
        scores["faithfulness"] = await faithfulness.single_turn_ascore(
            SingleTurnSample(
                user_input=case.question,
                response=trace.answer,
                retrieved_contexts=trace.contexts,
            )
        )
    return scores


def aggregate(per_case: dict[str, Scores]) -> dict[str, float]:
    """Mean of every metric across the cases where it was applicable."""
    totals: dict[str, list[float]] = {}
    for scores in per_case.values():
        for name, value in scores.items():
            if value is not None:
                totals.setdefault(name, []).append(value)
    return {name: sum(values) / len(values) for name, values in sorted(totals.items())}
