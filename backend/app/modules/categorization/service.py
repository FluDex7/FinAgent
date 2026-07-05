import json
import re
import uuid

from app.core.config import Settings
from app.modules.categorization.rules import DEFAULT_CATEGORIES, DEFAULT_RULES
from app.modules.transactions.models import MerchantSource
from app.modules.transactions.schemas import TransactionOut
from app.modules.transactions.service import TransactionsService
from app.shared.llm import get_chat_model

_LEADING_NAME_RE = re.compile(r"^[A-Za-zА-Яа-яЁё .&\-]+")
_CODE_FENCE_RE = re.compile(r"^```(?:json)?|```$", re.IGNORECASE | re.MULTILINE)

LLM_PROMPT_TEMPLATE = """Отнеси каждого продавца ниже к одной из категорий трат.

Категории: {categories}

Продавцы (JSON-массив строк): {merchants}

Верни ТОЛЬКО JSON-объект {{"ПРОДАВЕЦ": "Категория", ...}} без пояснений и markdown.
Если не уверен — используй категорию "Прочее"."""


def normalize_merchant(raw_description: str) -> str:
    """A rough merchant key: leading letters up to the first digit/city noise, uppercased."""
    match = _LEADING_NAME_RE.match(raw_description.strip())
    base = match.group(0) if match else raw_description
    return re.sub(r"\s+", " ", base).strip().upper()


def match_rule(normalized_key: str) -> str | None:
    for substring, category in DEFAULT_RULES.items():
        if substring in normalized_key:
            return category
    return None


class CategorizationService:
    def __init__(self, transactions: TransactionsService, settings: Settings) -> None:
        self.transactions = transactions
        self.settings = settings

    async def categorize_transactions(self, transactions: list[TransactionOut]) -> None:
        """Assigns merchant_id/category_id to freshly-parsed transactions.

        Cheap rule matches happen first; whatever's left goes through one
        batched LLM call and is cached in the merchants table so the same
        merchant is never sent to the LLM twice.
        """
        if not transactions:
            return

        by_key: dict[str, list[TransactionOut]] = {}
        for t in transactions:
            by_key.setdefault(normalize_merchant(t.raw_description), []).append(t)

        cache: dict[str, tuple[uuid.UUID, uuid.UUID | None]] = {}
        rule_matched: dict[str, str] = {}
        to_classify: list[str] = []

        for key in by_key:
            existing = await self.transactions.get_merchant(key)
            if existing is not None:
                cache[key] = existing
                continue
            rule_category = match_rule(key)
            if rule_category is not None:
                rule_matched[key] = rule_category
            else:
                to_classify.append(key)

        llm_matched = await self._classify_with_llm(to_classify) if to_classify else {}

        for key, txs in by_key.items():
            if key in cache:
                merchant_id, category_id = cache[key]
            else:
                category_name = rule_matched.get(key) or llm_matched.get(key, "Прочее")
                source = MerchantSource.rule if key in rule_matched else MerchantSource.llm
                category = await self.transactions.get_or_create_category(category_name)
                merchant_id = await self.transactions.upsert_merchant(
                    key, category.id, source
                )
                category_id = category.id
            for t in txs:
                await self.transactions.set_transaction_category(t.id, merchant_id, category_id)

    async def _classify_with_llm(self, merchant_keys: list[str]) -> dict[str, str]:
        try:
            # get_chat_model can itself raise (e.g. missing OPENAI_API_KEY) — deferred to
            # here, and inside the same try/except, so a bad LLM config never breaks a
            # CSV/PDF upload. Merchants just fall back to "Прочее" and can be recategorized
            # later once the provider is configured.
            chat_model = get_chat_model(self.settings)
            prompt = LLM_PROMPT_TEMPLATE.format(
                categories=", ".join(DEFAULT_CATEGORIES),
                merchants=json.dumps(merchant_keys, ensure_ascii=False),
            )
            response = await chat_model.ainvoke(prompt)
            content = (
                response.content if isinstance(response.content, str) else str(response.content)
            )
            raw = _CODE_FENCE_RE.sub("", content.strip()).strip()
            parsed = json.loads(raw)
            return {
                key: parsed[key] if parsed.get(key) in DEFAULT_CATEGORIES else "Прочее"
                for key in merchant_keys
            }
        except Exception:  # noqa: BLE001 - a flaky LLM must not break statement parsing
            return dict.fromkeys(merchant_keys, "Прочее")
