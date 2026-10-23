from enum import StrEnum

from app.domain.errors import InvalidTransition


class RunState(StrEnum):
    INTERVIEWING = "interviewing"
    AGENT_WORKING = "agent_working"
    AWAITING_USER = "awaiting_user"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    EXECUTING_TOOL = "executing_tool"
    SLICING = "slicing"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


TERMINAL_STATES = frozenset({RunState.COMPLETED, RunState.FAILED, RunState.ABORTED})
ACTIVE_STATES = frozenset(set(RunState) - TERMINAL_STATES)
WAITING_STATES = frozenset({RunState.AWAITING_USER, RunState.AWAITING_CONFIRMATION})

_STOP = {RunState.FAILED, RunState.ABORTED}

TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.INTERVIEWING: frozenset(
        {RunState.AWAITING_USER, RunState.EXECUTING_TOOL, RunState.AGENT_WORKING} | _STOP
    ),
    RunState.AGENT_WORKING: frozenset(
        {
            RunState.AWAITING_USER,
            RunState.AWAITING_CONFIRMATION,
            RunState.EXECUTING_TOOL,
            RunState.SLICING,
        }
        | _STOP
    ),
    RunState.AWAITING_USER: frozenset({RunState.INTERVIEWING, RunState.AGENT_WORKING} | _STOP),
    RunState.AWAITING_CONFIRMATION: frozenset(
        {RunState.EXECUTING_TOOL, RunState.AGENT_WORKING} | _STOP
    ),
    RunState.EXECUTING_TOOL: frozenset({RunState.INTERVIEWING, RunState.AGENT_WORKING} | _STOP),
    RunState.SLICING: frozenset({RunState.SAVING, RunState.AGENT_WORKING} | _STOP),
    RunState.SAVING: frozenset({RunState.COMPLETED, RunState.AGENT_WORKING} | _STOP),
    RunState.COMPLETED: frozenset(),
    RunState.FAILED: frozenset(),
    RunState.ABORTED: frozenset(),
}


def ensure_transition(current: RunState, target: RunState) -> None:
    if target not in TRANSITIONS[current]:
        raise InvalidTransition(f"Run cannot move from {current.value} to {target.value}")


def resume_state(requirements_ready: bool) -> RunState:
    return RunState.AGENT_WORKING if requirements_ready else RunState.INTERVIEWING
