from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Response, UploadFile
from pydantic import BaseModel

from app.controller.auth import InstanceDep, ServicesDep
from app.controller.downloads import attachment_disposition
from app.domain.confirmation import Decision

router = APIRouter(prefix="/runs", tags=["runs"])


class RunResponse(BaseModel):
    id: str
    conversation_id: str
    state: str
    requirements_ready: bool
    help_required: bool
    last_error: str | None


class ConfirmationRequest(BaseModel):
    decision: Literal["accept", "reject", "clarify"]
    text: str | None = None


class ArtifactResponse(BaseModel):
    id: str
    kind: str
    scene_epoch: str
    scene_version: int
    name: str
    content_type: str
    size: int
    sha256: str
    created_at: datetime


class ChunkResponse(BaseModel):
    complete: bool
    received: int
    artifact: ArtifactResponse | None


def _run(
    run_id: str, conversation_id: str, state: str, ready: bool, help_: bool, error: str | None
) -> RunResponse:
    return RunResponse(
        id=run_id,
        conversation_id=conversation_id,
        state=state,
        requirements_ready=ready,
        help_required=help_,
        last_error=error,
    )


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str, instance: InstanceDep, services: ServicesDep) -> RunResponse:
    run = await services.runs.get(instance.id, run_id)
    return _run(
        run.id,
        run.conversation_id,
        run.state.value,
        run.requirements_ready,
        run.help_required,
        run.last_error,
    )


@router.post("/{run_id}/confirmation", response_model=RunResponse)
async def confirm(
    run_id: str, body: ConfirmationRequest, instance: InstanceDep, services: ServicesDep
) -> RunResponse:
    run = await services.runs.confirm(instance.id, run_id, Decision(body.decision), body.text)
    return _run(
        run.id,
        run.conversation_id,
        run.state.value,
        run.requirements_ready,
        run.help_required,
        run.last_error,
    )


@router.post("/{run_id}/stop", response_model=RunResponse)
async def stop(run_id: str, instance: InstanceDep, services: ServicesDep) -> RunResponse:
    run = await services.runs.stop(instance.id, run_id)
    return _run(
        run.id,
        run.conversation_id,
        "aborted",
        run.requirements_ready,
        run.help_required,
        run.last_error,
    )


@router.get("/{run_id}/artifacts", response_model=list[ArtifactResponse])
async def list_artifacts(
    run_id: str, instance: InstanceDep, services: ServicesDep
) -> list[ArtifactResponse]:
    items = await services.artifacts.list(instance.id, run_id)
    return [
        ArtifactResponse(
            id=item.id,
            kind=item.kind,
            scene_version=item.scene_version,
            scene_epoch=item.scene_epoch,
            name=item.name,
            content_type=item.content_type,
            size=item.size,
            sha256=item.sha256,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.post("/{run_id}/artifacts", response_model=ChunkResponse)
async def upload_artifact_chunk(
    run_id: str,
    instance: InstanceDep,
    services: ServicesDep,
    file: Annotated[UploadFile, File()],
    kind: Annotated[str, Form()],
    scene_version: Annotated[int, Form()],
    scene_epoch: Annotated[str, Form()],
    chunk_index: Annotated[int, Form()],
    chunk_count: Annotated[int, Form()],
    sha256: Annotated[str, Form()],
) -> ChunkResponse:
    receipt = await services.artifacts.put_chunk(
        instance.id,
        run_id,
        kind=kind,
        scene_version=scene_version,
        scene_epoch=scene_epoch,
        chunk_index=chunk_index,
        chunk_count=chunk_count,
        sha256=sha256,
        data=await file.read(),
    )
    meta = receipt.artifact
    return ChunkResponse(
        complete=receipt.complete,
        received=receipt.received,
        artifact=None
        if meta is None
        else ArtifactResponse(
            id=meta.id,
            kind=meta.kind,
            scene_version=meta.scene_version,
            scene_epoch=meta.scene_epoch,
            name=meta.name,
            content_type=meta.content_type,
            size=meta.size,
            sha256=meta.sha256,
            created_at=meta.created_at,
        ),
    )


@router.get("/{run_id}/artifacts/{kind}")
async def download_artifact(
    run_id: str, kind: str, instance: InstanceDep, services: ServicesDep
) -> Response:
    blob = await services.artifacts.get(instance.id, run_id, kind)
    return Response(
        content=blob.data,
        media_type=blob.meta.content_type,
        headers={"Content-Disposition": attachment_disposition(blob.meta.name)},
    )
