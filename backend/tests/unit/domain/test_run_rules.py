import pytest

from app.domain.artifacts import verify_sha256
from app.domain.confirmation import BatchStatus, Mode, batch_hash, permits_execution
from app.domain.corrections import CorrectionState, limit_reached, operation_key, register_outcome
from app.domain.errors import ChecksumMismatch, InvalidRequest, InvalidTransition
from app.domain.jsonvalue import JsonObject
from app.domain.operations import validate_tool_arguments
from app.domain.run import RunState, ensure_transition

OPS: list[JsonObject] = [{"kind": "arrange"}]


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RunState.INTERVIEWING, RunState.AWAITING_USER),
        (RunState.AGENT_WORKING, RunState.AWAITING_CONFIRMATION),
        (RunState.SLICING, RunState.SAVING),
        (RunState.SAVING, RunState.COMPLETED),
    ],
)
def test_allowed_transitions(current: RunState, target: RunState) -> None:
    ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RunState.INTERVIEWING, RunState.AWAITING_CONFIRMATION),
        (RunState.INTERVIEWING, RunState.SLICING),
        (RunState.COMPLETED, RunState.AGENT_WORKING),
        (RunState.AWAITING_CONFIRMATION, RunState.SLICING),
    ],
)
def test_forbidden_transitions(current: RunState, target: RunState) -> None:
    with pytest.raises(InvalidTransition):
        ensure_transition(current, target)


def permit(
    mode: Mode,
    status: BatchStatus,
    *,
    operations: list[JsonObject] | None = None,
    scene: int = 3,
    batch_scene: int = 3,
) -> bool:
    return permits_execution(
        mode=mode,
        operations=operations if operations is not None else OPS,
        scene_version=scene,
        batch_status=status,
        batch_hash_value=batch_hash(OPS),
        batch_scene_version=batch_scene,
    )


def test_auto_mode_executes_without_decision() -> None:
    assert permit(Mode.AUTO, BatchStatus.ACCEPTED)


def test_ask_mode_needs_acceptance_bound_to_content_and_scene() -> None:
    assert not permit(Mode.ASK, BatchStatus.PROPOSED)
    assert permit(Mode.ASK, BatchStatus.ACCEPTED)
    assert not permit(Mode.ASK, BatchStatus.ACCEPTED, scene=4)
    assert not permit(Mode.ASK, BatchStatus.ACCEPTED, operations=[{"kind": "delete"}])
    assert not permit(Mode.ASK, BatchStatus.EXECUTED)


def test_correction_limit_counts_consecutive_failures_per_operation() -> None:
    state = CorrectionState()
    for _ in range(2):
        state = register_outcome(state, "apply_changes:set_global_setting:x", succeeded=False)
    assert not limit_reached(state, 3)
    state = register_outcome(state, "apply_changes:set_global_setting:x", succeeded=False)
    assert limit_reached(state, 3)
    assert (
        register_outcome(state, "apply_changes:set_global_setting:x", succeeded=True)
        == CorrectionState()
    )
    other = register_outcome(state, "slice", succeeded=False)
    assert other.failures == 1 and other.key == "slice"


def test_operation_key_points_at_first_unapplied_operation() -> None:
    arguments: JsonObject = {
        "operations": [
            {"kind": "select_profile", "profile_id": "p"},
            {"kind": "set_global_setting", "key": "layer_height", "value": 0.2},
        ]
    }
    assert operation_key("apply_changes", arguments, 1) == (
        "apply_changes:set_global_setting:layer_height"
    )
    assert operation_key("slice", {}, 0) == "slice"


def test_apply_changes_validation() -> None:
    validate_tool_arguments(
        "apply_changes",
        {
            "operations": [
                {"kind": "transform", "object_id": "o", "frame": "scene", "position_mm": [0, 0, 0]}
            ]
        },
    )
    bad_arguments: list[JsonObject] = [
        {"operations": [{"kind": "transform", "object_id": "o", "frame": "scene"}]},
        {
            "operations": [
                {
                    "kind": "transform",
                    "object_id": "o",
                    "frame": "scene",
                    "rotation_deg": [0, 0, 90],
                }
            ]
        },
        {"operations": [{"kind": "select_material", "material_id": "m"}]},
        {"operations": [{"kind": "unknown"}]},
        {"operations": []},
    ]
    for bad in bad_arguments:
        with pytest.raises(InvalidRequest):
            validate_tool_arguments("apply_changes", bad)
    with pytest.raises(InvalidRequest):
        validate_tool_arguments("nope", {})


def test_checksum_verification() -> None:
    import hashlib

    digest = hashlib.sha256(b"abc").hexdigest()
    assert verify_sha256(digest.upper(), b"abc") == digest
    with pytest.raises(ChecksumMismatch):
        verify_sha256(digest, b"abd")
