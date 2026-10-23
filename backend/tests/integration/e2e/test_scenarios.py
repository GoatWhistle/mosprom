import hashlib

import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from tests.integration.e2e.harness import (
    ScriptedLlm,
    Session,
    build_client,
    hello,
    next_event,
    next_tool_call,
    ok_result,
    open_session,
    text_reply,
    tool_reply,
    wait_state,
)

pytestmark = pytest.mark.integration

REQUIREMENTS = ("r1", "ask_user", {"questions": [], "requirements_summary": "PLA, fast"})
CHANGES = (
    "c1",
    "apply_changes",
    {
        "operations": [{"kind": "select_material", "material_id": "pla", "extruder": 0}],
        "explanation": "Use PLA",
    },
)


def upload(session: Session, run_id: str, kind: str, scene: int, data: bytes) -> None:
    digest = hashlib.sha256(data).hexdigest()
    half = len(data) // 2
    for index, part in enumerate((data[:half], data[half:])):
        response = session.post(
            f"/runs/{run_id}/artifacts",
            data={
                "kind": kind,
                "scene_version": str(scene),
                "chunk_index": str(index),
                "chunk_count": "2",
                "sha256": digest,
            },
            files={"file": ("part", part)},
        )
        assert response.status_code == 200, response.text


@pytest.fixture
def dsn(postgres_dsn: str, pool: AsyncConnectionPool[AsyncConnection]) -> str:
    return postgres_dsn


def test_auto_mode_runs_to_completed_with_both_artifacts(dsn: str) -> None:
    llm = ScriptedLlm(
        [
            tool_reply(("q1", "ask_user", {"questions": [{"text": "Which material?"}]})),
            tool_reply(REQUIREMENTS),
            tool_reply(CHANGES),
            tool_reply(("s1", "slice", {})),
            text_reply("Done: PLA at defaults."),
        ]
    )
    with build_client(dsn, llm) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "auto"}).json()["id"]
        with session.connect() as ws:
            hello(ws)
            sent = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print this"}
            )
            assert sent.status_code == 202
            run_id = sent.json()["run_id"]
            question = next_event(ws, "question")
            assert question["payload"]["questions"] == ["Which material?"]
            wait_state(session, run_id, "awaiting_user")
            session.post(f"/conversations/{conversation}/messages", json={"text": "PLA, fast"})
            call = next_tool_call(ws)
            assert call["tool"] == "apply_changes"
            assert call["expected_scene_version"] == 1
            ws.send_json(ok_result(call, 2))
            slice_call = next_tool_call(ws)
            assert slice_call["tool"] == "slice"
            ws.send_json(ok_result(slice_call, 2, layers=120))
            wait_state(session, run_id, "saving")
            gcode, archive = b"G1 X0 Y0\n" * 50, b"PK3MF" * 100
            upload(session, run_id, "gcode", 2, gcode)
            upload(session, run_id, "3mf", 2, archive)
            wait_state(session, run_id, "completed")
        assert session.get(f"/runs/{run_id}/artifacts/gcode").content == gcode
        assert session.get(f"/runs/{run_id}/artifacts/3mf").content == archive
        messages = session.get(f"/conversations/{conversation}").json()["messages"]
        assert messages[-1]["content"] == "Done: PLA at defaults."
        assert len(llm.requests) == 5
        roles = [message["role"] for message in llm.requests[2]["messages"]]
        assert "tool" in roles
        assert not llm.replies


def test_changes_are_blocked_until_requirements_are_ready(dsn: str) -> None:
    llm = ScriptedLlm(
        [
            tool_reply(CHANGES),
            tool_reply(("q1", "ask_user", {"questions": [{"text": "Material?"}]})),
        ]
    )
    with build_client(dsn, llm) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "auto"}).json()["id"]
        with session.connect() as ws:
            hello(ws)
            run_id = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print"}
            ).json()["run_id"]
            next_event(ws, "question")
            wait_state(session, run_id, "awaiting_user")
        tool_messages = [m for m in llm.requests[1]["messages"] if m["role"] == "tool"]
        assert "requirements_not_ready" in tool_messages[0]["content"]


def test_ask_mode_waits_for_confirmation_and_rejects_stale_scene(dsn: str) -> None:
    llm = ScriptedLlm(
        [
            tool_reply(REQUIREMENTS),
            tool_reply(CHANGES),
            tool_reply(CHANGES),
            text_reply("Waiting for you"),
        ]
    )
    with build_client(dsn, llm) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "ask"}).json()["id"]
        with session.connect() as ws:
            hello(ws)
            run_id = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print"}
            ).json()["run_id"]
            confirmation = next_event(ws, "confirmation_request")
            assert confirmation["payload"]["explanation"] == "Use PLA"
            wait_state(session, run_id, "awaiting_confirmation")
            ws.send_json({"type": "state_snapshot", "id": "s2", "scene_version": 2, "state": {}})
            import time

            time.sleep(0.3)
            accepted = session.post(f"/runs/{run_id}/confirmation", json={"decision": "accept"})
            assert accepted.status_code == 200
            second = next_event(ws, "confirmation_request")
            assert second["payload"]["scene_version"] == 2
            wait_state(session, run_id, "awaiting_confirmation")
            session.post(f"/runs/{run_id}/confirmation", json={"decision": "accept"})
            call = next_tool_call(ws)
            assert call["expected_scene_version"] == 2
            assert call["arguments"]["operations"][0]["kind"] == "select_material"
        tool_messages = [m for m in llm.requests[2]["messages"] if m["role"] == "tool"]
        assert any("stale_scene" in m["content"] for m in tool_messages)


def test_duplicate_tool_result_is_idempotent_and_stop_aborts(dsn: str) -> None:
    llm = ScriptedLlm([tool_reply(REQUIREMENTS), tool_reply(CHANGES), text_reply("ok")])
    with build_client(dsn, llm) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "auto"}).json()["id"]
        with session.connect() as ws:
            hello(ws)
            run_id = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print"}
            ).json()["run_id"]
            call = next_tool_call(ws)
            ws.send_json(ok_result(call, 2))
            ws.send_json(ok_result(call, 5, ignored=True))
            wait_state(session, run_id, "awaiting_user")
            stopped = session.post(f"/runs/{run_id}/stop")
            assert stopped.status_code == 200
            assert session.get(f"/runs/{run_id}").json()["state"] == "aborted"
            assert session.post(f"/runs/{run_id}/stop").status_code == 409
        final_context = llm.requests[2]["messages"][-1]["content"]
        assert '"scene_version": 2' in final_context


def test_correction_limit_requests_help_instead_of_looping(dsn: str) -> None:
    failing = {"ok": False, "error": {"code": "setting_rejected", "message": "bad"}}
    llm = ScriptedLlm(
        [tool_reply(REQUIREMENTS)]
        + [tool_reply((f"c{i}", "apply_changes", CHANGES[2])) for i in range(3)]
        + [text_reply("I cannot fix this; please advise.")]
    )
    with build_client(dsn, llm, correction_limit=3) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "auto"}).json()["id"]
        with session.connect() as ws:
            hello(ws)
            run_id = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print"}
            ).json()["run_id"]
            for _ in range(3):
                call = next_tool_call(ws)
                ws.send_json(
                    {
                        "type": "tool_result",
                        "id": "r",
                        "call_id": call["call_id"],
                        "run_id": run_id,
                        **failing,
                        "scene_version": 1,
                        "result": {},
                        "applied": [],
                    }
                )
            wait_state(session, run_id, "awaiting_user")
        run = session.get(f"/runs/{run_id}").json()
        assert run["help_required"] is True
        assert len(llm.requests) == 5


def test_missing_llm_connection_fails_with_explicit_error(dsn: str) -> None:
    llm = ScriptedLlm([])
    with build_client(dsn, llm) as client:
        registered = client.post("/api/v1/instances/register", json={"instance_id": "no-llm"})
        token = registered.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        conversation = client.post("/api/v1/conversations", headers=headers, json={}).json()["id"]
        run_id = client.post(
            f"/api/v1/conversations/{conversation}/messages", headers=headers, json={"text": "hi"}
        ).json()["run_id"]
        import time

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            run = client.get(f"/api/v1/runs/{run_id}", headers=headers).json()
            if run["state"] == "failed":
                break
            time.sleep(0.05)
        assert run["state"] == "failed"
        assert run["last_error"].startswith("llm_not_configured")


def test_unauthorized_requests_are_rejected(dsn: str) -> None:
    with build_client(dsn, ScriptedLlm([])) as client:
        assert client.get("/api/v1/conversations").status_code == 401
        assert client.get("/api/v1/health").status_code == 200
