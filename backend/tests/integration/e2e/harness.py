import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from fastapi.testclient import TestClient
from starlette.testclient import WebSocketTestSession

from app.main import create_app
from app.settings import Settings
from app.usecase.config import AgentConfig

INSTANCE = "slicer-e2e"
EPOCH = "11111111-1111-4111-8111-111111111111"


def text_reply(text: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": text}, "finish_reason": "stop"}]}


def tool_reply(*calls: tuple[str, str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }
                        for call_id, name, arguments in calls
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    }


@dataclass
class ScriptedLlm:
    replies: list[dict[str, Any]]
    requests: list[dict[str, Any]] = field(default_factory=list)

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(json.loads(request.content))
        if not self.replies:
            return httpx.Response(500, text="script exhausted")
        return httpx.Response(200, json=self.replies.pop(0))

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handle)


def build_client(dsn: str, llm: ScriptedLlm, **agent: Any) -> TestClient:
    settings = Settings(
        database_url=dsn,
        pool_max_size=8,
        agent=AgentConfig(tool_timeout_s=5, save_timeout_s=5, slice_timeout_s=5, **agent),
    )
    return TestClient(create_app(settings, llm.transport))


@dataclass
class Session:
    client: TestClient
    token: str
    headers: dict[str, str]

    def post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.client.post(f"/api/v1{path}", headers=self.headers, **kwargs)

    def get(self, path: str) -> httpx.Response:
        return self.client.get(f"/api/v1{path}", headers=self.headers)

    def put(self, path: str, **kwargs: Any) -> httpx.Response:
        return self.client.put(f"/api/v1{path}", headers=self.headers, **kwargs)

    def connect(self) -> WebSocketTestSession:
        return self.client.websocket_connect(f"/api/v1/instances/ws?token={self.token}")


def open_session(client: TestClient, instance: str = INSTANCE) -> Session:
    registered = client.post("/api/v1/instances/register", json={"instance_id": instance})
    assert registered.status_code == 201, registered.text
    token = registered.json()["token"]
    session = Session(client, token, {"Authorization": f"Bearer {token}"})
    configured = session.put(
        "/instances/llm", json={"base_url": "http://llm/v1", "model": "m", "api_key": "k"}
    )
    assert configured.status_code == 200
    return session


def hello(ws: WebSocketTestSession, scene_state: dict[str, Any] | None = None) -> dict[str, Any]:
    ws.send_json(
        {
            "type": "hello",
            "id": "h1",
            "contract_version": "2",
            "scene_epoch": EPOCH,
            "instance_id": INSTANCE,
            "slicer_version": "5.2.4",
            "modes": ["classic", "cylindrical"],
            "printer": {"name": "Hybrid 530"},
        }
    )
    ack = ws.receive_json()
    assert ack["type"] == "hello_ack", ack
    ws.send_json(
        {
            "type": "state_snapshot",
            "scene_epoch": EPOCH,
            "id": "s1",
            "scene_version": 1,
            "state": scene_state or {},
        }
    )
    ws.send_json({"type": "pending_calls", "id": "p1", "call_ids": []})
    return ack


def receive_until(
    ws: WebSocketTestSession, matches: Callable[[dict[str, Any]], bool]
) -> dict[str, Any]:
    for _ in range(50):
        frame = ws.receive_json()
        if matches(frame):
            return frame
    raise AssertionError("expected frame never arrived")


def next_event(ws: WebSocketTestSession, event: str) -> dict[str, Any]:
    return receive_until(ws, lambda frame: frame.get("event") == event)


def next_tool_call(ws: WebSocketTestSession) -> dict[str, Any]:
    return receive_until(ws, lambda frame: frame.get("type") == "tool_call")


def ok_result(call: dict[str, Any], scene_version: int, **extra: Any) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "id": "r-" + call["call_id"],
        "call_id": call["call_id"],
        "run_id": call["run_id"],
        "ok": True,
        "scene_version": scene_version,
        "scene_epoch": call["expected_scene_epoch"],
        "result": extra,
        "error": None,
        "applied": [],
    }


def wait_state(session: Session, run_id: str, state: str) -> dict[str, Any]:
    import time

    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        run = session.get(f"/runs/{run_id}").json()
        if run["state"] == state:
            return run
        time.sleep(0.05)
    raise AssertionError(f"run never reached {state}: {session.get(f'/runs/{run_id}').json()}")
