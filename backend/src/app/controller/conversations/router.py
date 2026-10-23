from typing import Annotated

from fastapi import APIRouter, File, Response, UploadFile
from fastapi.params import Query

from app.controller.auth import InstanceDep, ServicesDep
from app.controller.conversations.schemas import (
    AttachmentResponse,
    ConversationDetail,
    ConversationPageResponse,
    ConversationResponse,
    CreateConversationRequest,
    MessageResponse,
    ModeRequest,
    ProjectRequest,
    SendMessageRequest,
    SendMessageResponse,
)
from app.controller.downloads import attachment_disposition
from app.domain.confirmation import Mode

router = APIRouter(tags=["conversations"])


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    body: CreateConversationRequest, instance: InstanceDep, services: ServicesDep
) -> ConversationResponse:
    created = await services.conversations.create(instance.id, body.title, Mode(body.mode))
    return ConversationResponse.of(created)


@router.get("/conversations", response_model=ConversationPageResponse)
async def list_conversations(
    instance: InstanceDep,
    services: ServicesDep,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ConversationPageResponse:
    page = await services.conversations.list(instance.id, cursor, limit)
    return ConversationPageResponse(
        items=[ConversationResponse.of(item) for item in page.items], next_cursor=page.next_cursor
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str, instance: InstanceDep, services: ServicesDep
) -> ConversationDetail:
    conversation, messages, runtime = await services.conversations.get(instance.id, conversation_id)
    return ConversationDetail(
        conversation=ConversationResponse.of(conversation),
        messages=[MessageResponse.of(item) for item in messages],
        runtime=runtime,
    )


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=202,
)
async def send_message(
    conversation_id: str, body: SendMessageRequest, instance: InstanceDep, services: ServicesDep
) -> SendMessageResponse:
    accepted = await services.runs.post_message(
        instance.id,
        conversation_id,
        body.text,
        tuple(body.attachment_ids),
        Mode(body.mode) if body.mode else None,
        body.client_message_id,
    )
    return SendMessageResponse(run_id=accepted.run.id, message_id=accepted.message.id)


@router.put("/conversations/{conversation_id}/mode", response_model=ConversationResponse)
async def set_mode(
    conversation_id: str, body: ModeRequest, instance: InstanceDep, services: ServicesDep
) -> ConversationResponse:
    updated = await services.conversations.set_mode(instance.id, conversation_id, Mode(body.mode))
    return ConversationResponse.of(updated)


@router.put("/conversations/{conversation_id}/project", response_model=ConversationResponse)
async def set_project(
    conversation_id: str, body: ProjectRequest, instance: InstanceDep, services: ServicesDep
) -> ConversationResponse:
    updated = await services.conversations.set_project(
        instance.id, conversation_id, body.state, body.sha256, body.active
    )
    return ConversationResponse.of(updated)


@router.put("/conversations/{conversation_id}/active", response_model=ConversationResponse)
async def activate_conversation(
    conversation_id: str, instance: InstanceDep, services: ServicesDep
) -> ConversationResponse:
    activated = await services.conversations.activate(instance.id, conversation_id)
    return ConversationResponse.of(activated)


@router.post("/attachments", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(
    file: Annotated[UploadFile, File()], instance: InstanceDep, services: ServicesDep
) -> AttachmentResponse:
    data = await file.read()
    meta = await services.conversations.add_attachment(
        instance.id, file.filename or "", file.content_type, data
    )
    return AttachmentResponse.of(meta)


@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: str, instance: InstanceDep, services: ServicesDep
) -> Response:
    blob = await services.conversations.get_attachment(instance.id, attachment_id)
    return Response(
        content=blob.data,
        media_type=blob.meta.content_type,
        headers={"Content-Disposition": attachment_disposition(blob.meta.name)},
    )
