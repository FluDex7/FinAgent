from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.core.config import Settings
from app.modules.statements.service import StatementsService
from app.modules.tools.compare_periods import build_compare_periods_tool
from app.modules.tools.find_subscriptions import build_find_subscriptions_tool
from app.modules.tools.plot_chart import plot_chart
from app.modules.tools.rag_lookup import build_rag_lookup_tool
from app.modules.tools.read_document import build_read_document_tool
from app.modules.tools.sql_query import build_sql_query_tool
from app.modules.tools.web_search import build_web_search_tool
from app.modules.transactions.service import TransactionsService


def build_tools(
    transactions_service: TransactionsService,
    statements_service: StatementsService,
    chat_model: BaseChatModel,
    settings: Settings,
) -> list[BaseTool]:
    tools: list[BaseTool] = [
        build_sql_query_tool(transactions_service, chat_model),
        plot_chart,
        build_compare_periods_tool(transactions_service),
        build_find_subscriptions_tool(transactions_service),
        build_rag_lookup_tool(settings),
        build_read_document_tool(statements_service),
    ]
    web_search = build_web_search_tool(settings)
    if web_search is not None:
        tools.append(web_search)
    return tools
