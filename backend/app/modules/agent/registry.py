from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.core.config import Settings
from app.modules.tools.compare_periods import build_compare_periods_tool
from app.modules.tools.plot_chart import plot_chart
from app.modules.tools.rag_lookup import build_rag_lookup_tool
from app.modules.tools.sql_query import build_sql_query_tool
from app.modules.transactions.service import TransactionsService


def build_tools(
    transactions_service: TransactionsService, chat_model: BaseChatModel, settings: Settings
) -> list[BaseTool]:
    return [
        build_sql_query_tool(transactions_service, chat_model),
        plot_chart,
        build_compare_periods_tool(transactions_service),
        build_rag_lookup_tool(settings),
    ]
