from collections.abc import Iterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class FakeToolCallingChatModel(BaseChatModel):
    """Fake model returning canned AIMessages in order (bind_tools is a no-op).

    Implements _stream so tests can also exercise the token-streaming SSE path.
    """

    responses: list[AIMessage]

    def bind_tools(self, tools: object, **kwargs: object) -> "FakeToolCallingChatModel":
        return self

    def _generate(
        self,
        messages: object,
        stop: object = None,
        run_manager: object = None,
        **kwargs: object,
    ) -> ChatResult:
        message = self.responses.pop(0)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _stream(
        self,
        messages: object,
        stop: object = None,
        run_manager: object = None,
        **kwargs: object,
    ) -> Iterator[ChatGenerationChunk]:
        message = self.responses.pop(0)
        content = message.content if isinstance(message.content, str) else str(message.content)
        if message.tool_calls:
            yield ChatGenerationChunk(
                message=AIMessageChunk(content=content, tool_calls=message.tool_calls)
            )
            return
        for word in content.split(" "):
            yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling"
