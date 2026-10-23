import pytest

from app.adapter.llm.routing import ChatModelRouter, UnavailableChatModel
from app.domain.chat import ChatMessage, ChatRequest, ChatResponse, LlmConnection, Role
from app.domain.errors import ModelFailure

REQUEST = ChatRequest(messages=(ChatMessage(role=Role.USER, text="hi"),))


class Named:
    def __init__(self, name: str) -> None:
        self.name = name
        self.closed = False

    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        return ChatResponse(text=self.name)

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize(
    ("base_url", "expected"),
    [
        ("https://api.example/v1", "openai"),
        ("claude-agent", "claude"),
        (" Claude-Agent://local ", "claude"),
        ("http://claude-agent/v1", "openai"),
    ],
)
async def test_routes_by_base_url_scheme(base_url: str, expected: str) -> None:
    router = ChatModelRouter(Named("openai"), {"claude-agent": Named("claude")})
    connection = LlmConnection(base_url=base_url, model="m", api_key="k")

    assert (await router.chat(connection, REQUEST)).text == expected


async def test_closes_every_model() -> None:
    default, claude = Named("openai"), Named("claude")

    await ChatModelRouter(default, {"claude-agent": claude}).aclose()

    assert default.closed and claude.closed


async def test_unavailable_model_names_the_reason() -> None:
    connection = LlmConnection(base_url="claude-agent", model="m", api_key="k")

    with pytest.raises(ModelFailure, match="LLM=true"):
        await UnavailableChatModel("build with LLM=true").chat(connection, REQUEST)
