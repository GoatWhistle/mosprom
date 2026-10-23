import hashlib
from dataclasses import replace
from datetime import datetime

from app.domain.confirmation import Mode
from app.domain.errors import InvalidRequest, NotFound, PayloadTooLarge
from app.domain.jsonvalue import JsonObject
from app.usecase.config import AgentConfig
from app.usecase.conversation_runtime import conversation_runtime
from app.usecase.dto.conversation import (
    AttachmentBlob,
    AttachmentDTO,
    ConversationDTO,
    ConversationPage,
    MessageDTO,
)
from app.usecase.interface.runtime import Clock, IdGenerator
from app.usecase.interface.storage import UnitOfWorkFactory

ALLOWED_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "model/stl",
        "model/obj",
        "model/3mf",
        "application/octet-stream",
        "application/vnd.ms-package.3dmanufacturing-3dmodel+xml",
    }
)
ALLOWED_SUFFIXES = (".jpg", ".jpeg", ".png", ".stl", ".obj", ".3mf")
SUFFIX_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".stl": "model/stl",
    ".obj": "model/obj",
    ".3mf": "model/3mf",
}
PAGE_LIMIT = 50


class ConversationService:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, clock: Clock, ids: IdGenerator, config: AgentConfig
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._config = config

    async def create(self, instance_id: str, title: str, mode: Mode) -> ConversationDTO:
        now = self._clock.now()
        conversation = ConversationDTO(
            id=self._ids.new_id(),
            instance_id=instance_id,
            title=title.strip() or "New conversation",
            mode=mode,
            created_at=now,
            updated_at=now,
        )
        async with self._uow_factory() as uow:
            await uow.conversations.create(conversation)
            await uow.commit()
        return conversation

    async def get(
        self, instance_id: str, conversation_id: str
    ) -> tuple[ConversationDTO, list[MessageDTO], JsonObject]:
        async with self._uow_factory() as uow:
            await uow.read_snapshot()
            conversation = await uow.conversations.get(conversation_id)
            if conversation is None or conversation.instance_id != instance_id:
                raise NotFound()
            messages = await uow.conversations.list_messages(conversation_id)
            runtime = await conversation_runtime(uow, conversation_id)
            return conversation, messages, runtime

    async def list(self, instance_id: str, cursor: str | None, limit: int) -> ConversationPage:
        size = max(1, min(limit, PAGE_LIMIT))
        after = _decode_cursor(cursor)
        async with self._uow_factory() as uow:
            items = await uow.conversations.list_page(instance_id, size + 1, after)
        page = items[:size]
        next_cursor = None
        if len(items) > size:
            last = page[-1]
            next_cursor = f"{last.created_at.isoformat()}|{last.id}"
        return ConversationPage(items=tuple(page), next_cursor=next_cursor)

    async def set_mode(self, instance_id: str, conversation_id: str, mode: Mode) -> ConversationDTO:
        async with self._uow_factory() as uow:
            conversation = await uow.conversations.get(conversation_id)
            if conversation is None or conversation.instance_id != instance_id:
                raise NotFound()
            await uow.conversations.set_mode(conversation_id, mode, self._clock.now())
            await uow.commit()
        return replace(conversation, mode=mode)

    async def add_attachment(
        self,
        instance_id: str,
        name: str,
        content_type: str | None,
        data: bytes,
        source: str = "user",
    ) -> AttachmentDTO:
        if len(data) > self._config.max_attachment_bytes:
            raise PayloadTooLarge()
        lowered = name.lower()
        suffix = next((item for item in ALLOWED_SUFFIXES if lowered.endswith(item)), None)
        if suffix is None:
            raise InvalidRequest("Supported attachments: JPG, PNG, STL, OBJ, 3MF")
        kind = content_type if content_type in ALLOWED_TYPES else SUFFIX_TYPES[suffix]
        if kind == "application/octet-stream":
            kind = SUFFIX_TYPES[suffix]
        meta = AttachmentDTO(
            id=self._ids.new_id(),
            instance_id=instance_id,
            conversation_id=None,
            source=source,
            name=name,
            content_type=kind,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            created_at=self._clock.now(),
        )
        async with self._uow_factory() as uow:
            await uow.attachments.add(AttachmentBlob(meta=meta, data=data))
            await uow.commit()
        return meta

    async def get_attachment(self, instance_id: str, attachment_id: str) -> AttachmentBlob:
        async with self._uow_factory() as uow:
            blob = await uow.attachments.get_blob(attachment_id)
        if blob is None or blob.meta.instance_id != instance_id:
            raise NotFound()
        return blob


def _decode_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    if not cursor:
        return None
    try:
        stamp, identifier = cursor.split("|", 1)
        return datetime.fromisoformat(stamp), identifier
    except ValueError:
        raise InvalidRequest("Invalid cursor") from None
