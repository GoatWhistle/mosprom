import json
from datetime import UTC, datetime
from typing import cast

from app.domain.run import RunState
from app.usecase.context import build_messages
from app.usecase.dto.instance import InstanceDTO
from app.usecase.dto.run import RunDTO
from app.usecase.interface.storage import UnitOfWork

NOW = datetime(2026, 10, 23, tzinfo=UTC)
RUN = RunDTO(
    id="r1",
    conversation_id="c1",
    instance_id="i1",
    state=RunState.AGENT_WORKING,
    created_at=NOW,
    updated_at=NOW,
)


async def context_text(state: dict[str, object]) -> str:
    instance = InstanceDTO(id="i1", token_hash="h", state=state)  # type: ignore[arg-type]
    messages = await build_messages(cast(UnitOfWork, None), "system", RUN, [], instance, [], "ask")
    return messages[-1].text


async def test_settings_are_rendered_as_text_after_the_scene_json() -> None:
    text = await context_text(
        {
            "mode": "classic",
            "settings": [
                {"category": "speed", "settings": ["*speed_infill = 60 mm/s (float; 0.1..)"]},
                {"category": "support", "settings": ["support_enable = false (bool)"]},
            ],
        }
    )
    head, _, tail = text.partition("\n[current values")
    scene = json.loads(head.split("\n", 1)[1])["scene_state"]
    assert scene == {"mode": "classic"}
    assert "## speed\n*speed_infill = 60 mm/s (float; 0.1..)\n## support" in tail


async def test_state_without_settings_keeps_the_json_only_context() -> None:
    text = await context_text({"mode": "classic"})
    assert "[current values" not in text
    assert json.loads(text.split("\n", 1)[1])["scene_state"] == {"mode": "classic"}
