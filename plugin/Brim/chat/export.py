import datetime
import os
import re
import shutil

from ..agent.transcript import call_arguments, call_name
from ..execution.operations import MODEL_EXTENSIONS
from ..protocol import constants
from .entries_view import slice_result
from .files import safe_name
from .transcript_markdown import render_markdown

MARKDOWN_NAME = "chat.md"
PAGE_NAMES = re.compile(r"^chat_(text_)?\d+\.png$")
RESULT_NAMES = {"3mf": "project.3mf", "gcode": "result.gcode"}


def _model_files(messages):
    for message in messages:
        for item in message.get("brim_attachments") or []:
            yield item.get("name") or ""
    for message in messages:
        for call in message.get("tool_calls") or []:
            if call_name(call) == constants.TOOL_APPLY_CHANGES:
                for operation in call_arguments(call).get("operations") or []:
                    if isinstance(operation, dict) and operation.get("kind") in ("import_model", "open_3mf"):
                        yield safe_name(str(operation.get("path") or ""))


def model_name(chat):
    for name in _model_files(chat.get("messages") or []):
        stem, extension = os.path.splitext(name)
        if extension.lower() in MODEL_EXTENSIONS and stem.strip():
            return safe_name(stem.strip())
    return safe_name(chat.get("title") or "").strip(" .") or chat["id"][:8]


def latest_slice_files(messages):
    for message in reversed(messages):
        if message.get("role") == "tool" and message.get("brim_tool") == constants.TOOL_SLICE \
                and message.get("brim_status") == "ok":
            result = slice_result(message)
            if result is not None:
                return result["files"]
    return None


def _clear_pages(target):
    for name in os.listdir(target):
        if PAGE_NAMES.match(name):
            os.remove(os.path.join(target, name))


def _copy_results(files, target):
    copied = []
    for kind, name in sorted(RESULT_NAMES.items()):
        source = (files or {}).get(kind)
        if source and os.path.isfile(source):
            shutil.copyfile(source, os.path.join(target, name))
            copied.append(name)
    return copied


def prepare_export(root, chat, strings, model):
    target = os.path.join(root, model_name(chat))
    os.makedirs(target, exist_ok=True)
    _clear_pages(target)
    copied = _copy_results(latest_slice_files(chat.get("messages") or []), target)
    exported_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(os.path.join(target, MARKDOWN_NAME), "w", encoding="utf-8") as handle:
        handle.write(render_markdown(chat, strings, model, exported_at))
    return {"path": target, "copied": copied}
