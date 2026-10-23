import time

import pytest

from tests.integration.e2e.harness import (
    EPOCH,
    INSTANCE,
    ScriptedLlm,
    Session,
    build_client,
    hello,
    next_event,
    next_tool_call,
    open_session,
    text_reply,
    tool_reply,
    wait_state,
)
from tests.integration.e2e.test_scenarios import CHANGES, REQUIREMENTS

pytestmark = pytest.mark.integration
NEW_EPOCH = "33333333-3333-4333-8333-333333333333"


def test_backend_restart_waits_for_scene_and_llm(postgres_dsn: str, pool: object) -> None:
    llm = ScriptedLlm([text_reply("Ready to continue")])
    with build_client(postgres_dsn, llm) as client:
        session = open_session(client)
        token = session.token
        conversation = session.post("/conversations", json={}).json()["id"]
        run_id = session.post(
            f"/conversations/{conversation}/messages", json={"text": "Print a bracket"}
        ).json()["run_id"]
        assert not llm.requests
    with build_client(postgres_dsn, llm) as client:
        session = Session(client, token, {"Authorization": f"Bearer {token}"})
        with session.connect() as ws:
            hello(ws)
            time.sleep(0.05)
            run = session.get(f"/runs/{run_id}").json()
            assert run["state"] == "interviewing"
            assert run["last_error"] is None
            assert not llm.requests
            response = session.put(
                "/instances/llm", json={"base_url": "http://llm/v1", "model": "m", "api_key": "k"}
            )
            assert response.status_code == 200
            next_event(ws, "assistant_message")
            wait_state(session, run_id, "awaiting_user")
            assert len(llm.requests) == 1


def test_new_slicer_epoch_invalidates_confirmation(postgres_dsn: str, pool: object) -> None:
    llm = ScriptedLlm([tool_reply(REQUIREMENTS), tool_reply(CHANGES), tool_reply(CHANGES)])
    with build_client(postgres_dsn, llm) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "ask"}).json()["id"]
        with session.connect() as ws:
            hello(ws)
            run_id = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print"}
            ).json()["run_id"]
            next_event(ws, "confirmation_request")
            detail = session.get(f"/conversations/{conversation}").json()
            assert detail["runtime"]["pending"]["scene_epoch"] == EPOCH
            assert detail["runtime"]["state"] == "awaiting_confirmation"
        with session.connect() as ws:
            ws.send_json(
                {
                    "type": "hello",
                    "id": "new",
                    "contract_version": "2",
                    "instance_id": INSTANCE,
                    "scene_epoch": NEW_EPOCH,
                    "slicer_version": "7",
                    "modes": ["classic"],
                    "printer": {},
                }
            )
            assert ws.receive_json()["type"] == "hello_ack"
            ws.send_json(
                {
                    "type": "state_snapshot",
                    "id": "s",
                    "scene_epoch": NEW_EPOCH,
                    "scene_version": 1,
                    "state": {"objects": []},
                }
            )
            ws.send_json({"type": "pending_calls", "id": "p", "call_ids": []})
            time.sleep(0.05)
            response = session.post(f"/runs/{run_id}/confirmation", json={"decision": "accept"})
            assert response.status_code == 200
            renewed = next_event(ws, "confirmation_request")
            assert renewed["payload"]["scene_epoch"] == NEW_EPOCH
            session.post(f"/runs/{run_id}/confirmation", json={"decision": "accept"})
            call = next_tool_call(ws)
            assert call["expected_scene_epoch"] == NEW_EPOCH
            assert call["expected_scene_version"] == 1


def test_question_survives_reopening_conversation(postgres_dsn: str, pool: object) -> None:
    llm = ScriptedLlm([tool_reply(("q", "ask_user", {"questions": [{"text": "Load?"}]}))])
    with build_client(postgres_dsn, llm) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={}).json()["id"]
        with session.connect() as ws:
            hello(ws)
            run_id = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print"}
            ).json()["run_id"]
            next_event(ws, "question")
            runtime = session.get(f"/conversations/{conversation}").json()["runtime"]
            assert runtime["run_id"] == run_id
            assert runtime["pending"]["questions"] == ["Load?"]
            assert any(event["event"] == "question" for event in runtime["events"])


def test_old_protocol_is_rejected(postgres_dsn: str, pool: object) -> None:
    with build_client(postgres_dsn, ScriptedLlm([])) as client:
        session = open_session(client)
        with session.connect() as ws:
            ws.send_json(
                {"type": "hello", "id": "old", "contract_version": "1", "scene_epoch": EPOCH}
            )
            assert ws.receive_json()["code"] == "contract_mismatch"
