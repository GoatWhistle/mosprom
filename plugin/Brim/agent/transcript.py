import base64
import json

from . import ask_user

PRIVATE_PREFIX = "brim_"
REJECTED_TEXT = "the user rejected this call"


def call_name(call):
    return (call.get("function") or {}).get("name")


def call_arguments(call):
    raw = (call.get("function") or {}).get("arguments")
    if isinstance(raw, dict):
        return raw
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def rejected_text(comment):
    return REJECTED_TEXT + (": " + comment if comment else "")


def rejection_comment(message):
    text = str(message or "")
    return text[len(REJECTED_TEXT) + 2:].strip() if text.startswith(REJECTED_TEXT + ": ") else ""


def answered_ids(messages, start):
    return set(item.get("tool_call_id") for item in messages[start:] if item.get("role") == "tool")


def dangling_calls(messages):
    for index in range(len(messages) - 1, -1, -1):
        message = messages[index]
        if message.get("role") == "assistant":
            if not message.get("tool_calls"):
                return []
            answered = answered_ids(messages, index + 1)
            return [call for call in message["tool_calls"] if call.get("id") not in answered]
        if message.get("role") == "user" and not message.get("brim_hidden"):
            return []
    return []


def pending_question(messages):
    for call in dangling_calls(messages):
        if call_name(call) == ask_user.NAME:
            questions = ask_user.questions_of(call_arguments(call))
            if questions:
                return {"call_id": call.get("id"), "questions": questions}
    return None


def _data_url(image, read_file):
    data = read_file(image["path"])
    if data is None:
        return None
    return "data:%s;base64,%s" % (image.get("mime_type") or "image/png", base64.b64encode(data).decode("ascii"))


def wire_message(message, read_file):
    wire = dict((key, value) for key, value in message.items() if not key.startswith(PRIVATE_PREFIX))
    images = message.get("brim_images") or []
    if message.get("role") == "user" and images:
        parts = [{"type": "text", "text": message.get("content") or ""}]
        for image in images:
            url = _data_url(image, read_file)
            if url is not None:
                parts.append({"type": "image_url", "image_url": {"url": url}})
        wire["content"] = parts
    return wire


def wire_messages(messages, read_file):
    return [wire_message(message, read_file) for message in messages]
