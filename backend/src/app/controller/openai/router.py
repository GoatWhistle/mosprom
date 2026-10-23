from typing import Annotated

from fastapi import APIRouter, Body, Header, Request

from app.domain.errors import Unauthorized
from app.domain.jsonvalue import JsonObject
from app.usecase.completion import CompletionService

MODELS = ("sonnet", "opus", "haiku")
BEARER = "Bearer "

router = APIRouter(prefix="/v1", tags=["openai"])


def _token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith(BEARER):
        raise Unauthorized()
    token = authorization[len(BEARER) :].strip()
    if not token:
        raise Unauthorized()
    return token


@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: Annotated[JsonObject, Body()],
    authorization: Annotated[str | None, Header()] = None,
) -> JsonObject:
    service: CompletionService = request.app.state.completions
    return await service.complete(_token(authorization), body)


@router.get("/models")
async def models() -> JsonObject:
    return {
        "object": "list",
        "data": [{"id": name, "object": "model", "owned_by": "anthropic"} for name in MODELS],
    }
