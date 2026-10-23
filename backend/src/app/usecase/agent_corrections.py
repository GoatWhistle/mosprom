from dataclasses import replace

from app.domain.corrections import CorrectionState, limit_reached, operation_key, register_outcome
from app.domain.protocol import STALE_SCENE
from app.usecase.agent_flow import Flow
from app.usecase.dto.run import RunDTO
from app.usecase.dto.tools import CallStatus, ToolCallDTO
from app.usecase.run_store import RunStore
from app.usecase.tool_results import call_ok, error_code


async def correction_flow(
    run: RunDTO, call: ToolCallDTO, store: RunStore, limit_count: int
) -> Flow:
    if error_code(call) == "outcome_unknown" or call.status is CallStatus.OUTCOME_UNKNOWN:
        await store.save(run, lambda fresh: replace(fresh, help_required=True))
        return Flow.HELP
    if call.tool not in {"apply_changes", "slice"} or error_code(call) in {STALE_SCENE}:
        return Flow.CONTINUE
    key = operation_key(call.tool, call.arguments, len(call.applied))
    state = register_outcome(
        CorrectionState(run.correction_key, run.correction_failures),
        key,
        succeeded=call_ok(call),
    )
    limit = limit_reached(state, limit_count)
    await store.save(
        run,
        lambda fresh: replace(
            fresh,
            correction_key=state.key,
            correction_failures=state.failures,
            help_required=limit,
        ),
    )
    return Flow.HELP if limit and call.status is not CallStatus.COMPLETED else Flow.CONTINUE
