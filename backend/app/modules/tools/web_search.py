from langchain_core.tools import BaseTool
from langchain_tavily import TavilySearch

from app.core.config import Settings

WEB_SEARCH_DESCRIPTION = (
    "Ищет актуальную информацию в открытом интернете — курсы валют, текущие события, "
    "факты, которых не может быть в локальных данных пользователя (модель могла устареть "
    "или не знать). Используй, только когда без внешней проверки не обойтись. "
    "НИКОГДА не подставляй в поисковый запрос данные пользователя (суммы, продавцов, "
    "содержимое выписок) — это единственный инструмент FinAgent, который уходит за пределы "
    "локальной машины, и в него не должно попадать ничего из личных финансовых данных."
)


def build_web_search_tool(settings: Settings) -> BaseTool | None:
    """Optional — only registered when TAVILY_API_KEY is set. The one FinAgent tool
    that calls a third-party service; everything else stays fully local."""
    if not settings.tavily_api_key:
        return None
    return TavilySearch(
        tavily_api_key=settings.tavily_api_key,
        max_results=4,
        name="web_search",
        description=WEB_SEARCH_DESCRIPTION,
    )
