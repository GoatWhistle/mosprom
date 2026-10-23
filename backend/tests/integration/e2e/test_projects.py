import hashlib

import psycopg
import pytest
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from tests.integration.e2e.harness import (
    ScriptedLlm,
    Session,
    build_client,
    hello,
    next_tool_call,
    ok_result,
    open_session,
    text_reply,
    tool_reply,
    wait_state,
)
from tests.integration.e2e.test_scenarios import CHANGES, REQUIREMENTS, upload

pytestmark = pytest.mark.integration

DIGEST = hashlib.sha256(b"project").hexdigest()
EDITED = hashlib.sha256(b"edited").hexdigest()


@pytest.fixture
def dsn(postgres_dsn: str, pool: AsyncConnectionPool[AsyncConnection]) -> str:
    return postgres_dsn


def save_project(session: Session, conversation: str, **body: object) -> dict[str, object]:
    payload = {"state": "saved", "sha256": DIGEST, **body}
    response = session.put(f"/conversations/{conversation}/project", json=payload)
    assert response.status_code == 200, response.text
    project: dict[str, object] = response.json()["project"]
    return project


def test_new_conversation_has_no_project(dsn: str) -> None:
    with build_client(dsn, ScriptedLlm([])) as client:
        session = open_session(client)
        created = session.post("/conversations", json={}).json()
        assert created["project"] == {
            "state": "none",
            "version": 0,
            "sha256": None,
            "saved_at": None,
        }


def test_project_saves_bump_version_and_mark_the_active_conversation(dsn: str) -> None:
    with build_client(dsn, ScriptedLlm([])) as client:
        session = open_session(client)
        first = session.post("/conversations", json={}).json()["id"]
        second = session.post("/conversations", json={}).json()["id"]
        assert save_project(session, first)["version"] == 1
        assert save_project(session, first)["version"] == 1
        other_digest = hashlib.sha256(b"edited").hexdigest()
        assert save_project(session, first, sha256=other_digest)["version"] == 2
        empty = session.put(
            f"/conversations/{second}/project", json={"state": "empty", "sha256": DIGEST}
        ).json()["project"]
        assert empty["state"] == "empty" and empty["sha256"] is None
        detail = session.get(f"/conversations/{first}").json()["conversation"]["project"]
        assert detail["version"] == 2 and detail["sha256"] == other_digest
        with psycopg.connect(dsn) as connection:
            row = connection.execute("SELECT active_conversation_id FROM instances").fetchone()
        assert row is not None and str(row[0]) == second


def test_activating_a_conversation_updates_the_instance(dsn: str) -> None:
    with build_client(dsn, ScriptedLlm([])) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={}).json()["id"]
        assert session.put(f"/conversations/{conversation}/active").status_code == 200
        with psycopg.connect(dsn) as connection:
            row = connection.execute("SELECT active_conversation_id FROM instances").fetchone()
        assert row is not None and str(row[0]) == conversation
        other = open_session(client, "slicer-other")
        assert other.put(f"/conversations/{conversation}/active").status_code == 404


def test_saved_project_needs_a_digest_and_belongs_to_its_instance(dsn: str) -> None:
    with build_client(dsn, ScriptedLlm([])) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={}).json()["id"]
        missing = session.put(f"/conversations/{conversation}/project", json={"state": "saved"})
        assert missing.status_code == 422
        other = open_session(client, "slicer-other")
        foreign = other.put(
            f"/conversations/{conversation}/project", json={"state": "saved", "sha256": DIGEST}
        )
        assert foreign.status_code == 404


def test_resent_message_with_same_client_id_is_accepted_once(dsn: str) -> None:
    with build_client(dsn, ScriptedLlm([])) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "auto"}).json()["id"]
        body = {"text": "Print this", "client_message_id": "draft-1"}
        first = session.post(f"/conversations/{conversation}/messages", json=body)
        second = session.post(f"/conversations/{conversation}/messages", json=body)
        assert first.status_code == second.status_code == 202
        assert first.json() == second.json()
        messages = session.get(f"/conversations/{conversation}").json()["messages"]
        assert [item["role"] for item in messages].count("user") == 1


def test_result_records_the_project_version_it_was_built_from(dsn: str) -> None:
    llm = ScriptedLlm(
        [
            tool_reply(REQUIREMENTS),
            tool_reply(CHANGES),
            tool_reply(("s1", "slice", {})),
            text_reply("Done"),
        ]
    )
    with build_client(dsn, llm) as client:
        session = open_session(client)
        conversation = session.post("/conversations", json={"mode": "auto"}).json()["id"]
        save_project(session, conversation)
        save_project(session, conversation, sha256=EDITED)
        with session.connect() as ws:
            hello(ws)
            run_id = session.post(
                f"/conversations/{conversation}/messages", json={"text": "Print this"}
            ).json()["run_id"]
            call = next_tool_call(ws)
            ws.send_json(ok_result(call, 2))
            slice_call = next_tool_call(ws)
            ws.send_json(ok_result(slice_call, 2, layers=10))
            wait_state(session, run_id, "saving")
            upload(session, run_id, "gcode", 2, b"G1 X0\n" * 20)
            upload(session, run_id, "3mf", 2, b"PK3MF" * 20)
            wait_state(session, run_id, "completed")
        save_project(session, conversation, sha256=hashlib.sha256(b"later").hexdigest())
        detail = session.get(f"/conversations/{conversation}").json()
        assert detail["runtime"]["result"]["project_version"] == 2
        assert detail["conversation"]["project"]["version"] == 3
