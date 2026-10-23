import json
import uuid

from . import constants


class FrameError(ValueError):
    pass


def new_id():
    return uuid.uuid4().hex


def make_frame(frame_type, **fields):
    frame = {"type": frame_type, "id": new_id()}
    frame.update(fields)
    return frame


def encode_frame(frame):
    return json.dumps(frame, ensure_ascii=False, separators=(",", ":"))


def decode_frame(text):
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    try:
        frame = json.loads(text)
    except ValueError as error:
        raise FrameError("invalid json: %s" % error)
    if not isinstance(frame, dict):
        raise FrameError("frame must be an object")
    if not isinstance(frame.get("type"), str):
        raise FrameError("frame type missing")
    if not isinstance(frame.get("id"), str):
        raise FrameError("frame id missing")
    return frame


def hello_frame(instance_id, slicer_version, modes, printer):
    return make_frame(
        constants.HELLO,
        contract_version=constants.CONTRACT_VERSION,
        instance_id=instance_id,
        slicer_version=slicer_version,
        modes=list(modes),
        printer=printer,
    )


def snapshot_frame(scene_version, state):
    return make_frame(constants.STATE_SNAPSHOT, scene_version=scene_version, state=state)


def chat_message_frame(conversation_id, text, attachment_ids):
    return make_frame(
        constants.CHAT_MESSAGE,
        conversation_id=conversation_id,
        text=text,
        attachment_ids=list(attachment_ids),
    )


def tool_result_frame(call_id, run_id, ok, scene_version, result=None, error=None, applied=None):
    return make_frame(
        constants.TOOL_RESULT,
        call_id=call_id,
        run_id=run_id,
        ok=bool(ok),
        scene_version=scene_version,
        result=result if result is not None else {},
        error=error,
        applied=list(applied) if applied else [],
    )


def progress_frame(call_id, stage, fraction):
    return make_frame(constants.PROGRESS, call_id=call_id, stage=stage, fraction=fraction)


def mcp_response_frame(request_id, envelope):
    frame = make_frame(constants.MCP_RESPONSE, jsonrpc=envelope)
    frame["request_id"] = request_id
    return frame


def pending_calls_frame(call_ids):
    return make_frame(constants.PENDING_CALLS, call_ids=sorted(call_ids))


def error_object(code, message):
    return {"code": code, "message": message}
