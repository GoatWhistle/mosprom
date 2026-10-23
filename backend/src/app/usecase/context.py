import json

from app.domain.chat import ChatMessage, ImagePart, Role, ToolCall
from app.domain.jsonvalue import JsonObject
from app.usecase.dto.conversation import AttachmentDTO
from app.usecase.dto.instance import InstanceDTO
from app.usecase.dto.run import RunDTO, TranscriptEntry
from app.usecase.interface.storage import UnitOfWork

IMAGE_TYPES = frozenset({"image/jpeg", "image/png"})


async def build_messages(
    uow: UnitOfWork,
    system_prompt: str,
    run: RunDTO,
    transcript: list[TranscriptEntry],
    instance: InstanceDTO,
    attachments: list[AttachmentDTO],
    mode: str,
) -> list[ChatMessage]:
    messages = [ChatMessage(role=Role.SYSTEM, text=system_prompt)]
    for entry in transcript:
        messages.extend(await _entry_messages(uow, entry))
    messages.append(
        ChatMessage(role=Role.USER, text=_context_text(run, instance, attachments, mode))
    )
    return messages


async def _entry_messages(uow: UnitOfWork, entry: TranscriptEntry) -> list[ChatMessage]:
    images = await _images(uow, entry.attachment_ids)
    if entry.role == "tool":
        messages = [
            ChatMessage(role=Role.TOOL, text=entry.content, tool_call_id=entry.tool_call_id)
        ]
        if images:
            messages.append(
                ChatMessage(
                    role=Role.USER, text="Image returned by the previous tool.", images=images
                )
            )
        return messages
    calls = tuple(_tool_call(item) for item in entry.tool_calls)
    return [ChatMessage(role=Role(entry.role), text=entry.content, images=images, tool_calls=calls)]


async def _images(uow: UnitOfWork, attachment_ids: tuple[str, ...]) -> tuple[ImagePart, ...]:
    images = []
    for attachment_id in attachment_ids:
        blob = await uow.attachments.get_blob(attachment_id)
        if blob is not None and blob.meta.content_type in IMAGE_TYPES:
            images.append(ImagePart(mime_type=blob.meta.content_type, data=blob.data))
    return tuple(images)


def _context_text(
    run: RunDTO, instance: InstanceDTO, attachments: list[AttachmentDTO], mode: str
) -> str:
    context: JsonObject = {
        "requirements_ready": run.requirements_ready,
        "requirements_summary": run.requirements_summary,
        "mode": mode,
        "scene_version": instance.scene_version,
        "scene_epoch": instance.scene_epoch,
        "slicer_version": instance.slicer_version,
        "available_modes": list(instance.modes),
        "printer": instance.printer,
        "scene_state": instance.state,
        "attachments": [
            {"id": item.id, "name": item.name, "content_type": item.content_type, "size": item.size}
            for item in attachments
        ],
    }
    return "[scene context, refreshed every turn]\n" + json.dumps(context, ensure_ascii=False)


def _tool_call(item: JsonObject) -> ToolCall:
    arguments = item.get("arguments")
    return ToolCall(
        id=str(item["id"]),
        name=str(item["name"]),
        arguments=arguments if isinstance(arguments, dict) else {},
    )
