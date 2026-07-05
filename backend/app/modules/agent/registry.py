from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.modules.tools.plot_chart import plot_chart
from app.modules.tools.sql_query import build_sql_query_tool
from app.modules.transactions.service import TransactionsService


def build_tools(
    transactions_service: TransactionsService, chat_model: BaseChatModel
) -> list[BaseTool]:
    return [build_sql_query_tool(transactions_service, chat_model), plot_chart]
