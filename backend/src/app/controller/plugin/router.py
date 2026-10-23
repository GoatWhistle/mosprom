import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.controller.services import Services
from app.domain.errors import DomainError, Unauthorized
from app.domain.jsonvalue import JsonObject

router = APIRouter(tags=["plugin"])

CLOSE_UNAUTHORIZED = 4401
CLOSE_BAD_CONTRACT = 4409
CLOSE_BAD_FRAME = 4400


@router.websocket("/instances/ws")
async def plugin_socket(websocket: WebSocket, token: str = "") -> None:
    services: Services = websocket.app.state.services
    try:
        instance = await services.instances.authenticate(token)
    except Unauthorized:
        await websocket.close(code=CLOSE_UNAUTHORIZED)
        return
    await websocket.accept()

    async def sink(frame: JsonObject) -> None:
        await websocket.send_text(json.dumps(frame, ensure_ascii=False))

    try:
        first = await _receive(websocket)
        if first is None or first.get("type") != "hello":
            await websocket.close(code=CLOSE_BAD_FRAME)
            return
        responses = await services.session.handle(instance.id, first)
        for response in responses:
            await sink(response)
        if any(item.get("type") == "error" for item in responses):
            await websocket.close(code=CLOSE_BAD_CONTRACT)
            return
        services.registry.attach(instance.id, sink)
        while True:
            frame = await _receive(websocket)
            if frame is None:
                await sink(
                    {
                        "type": "error",
                        "code": "invalid_frame",
                        "message": "Frame must be a JSON object",
                    }
                )
                continue
            for response in await services.session.handle(instance.id, frame):
                await sink(response)
    except WebSocketDisconnect:
        pass
    except DomainError:
        await websocket.close(code=CLOSE_BAD_FRAME)
    finally:
        if services.registry.detach(instance.id, sink):
            services.session.disconnect(instance.id)


async def _receive(websocket: WebSocket) -> JsonObject | None:
    raw = await websocket.receive_text()
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None
