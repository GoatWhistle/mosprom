from dataclasses import dataclass

from app.domain.artifacts import (
    CONTENT_TYPES,
    ArtifactKind,
    parse_kind,
    verify_chunk_plan,
    verify_sha256,
)
from app.domain.errors import InvalidArtifact, NotFound, PayloadTooLarge
from app.domain.run import RunState
from app.usecase.config import AgentConfig
from app.usecase.dto.artifact import ArtifactBlob, ArtifactChunk, ArtifactDTO
from app.usecase.interface.runtime import CallSignals, Clock, IdGenerator
from app.usecase.interface.storage import UnitOfWorkFactory

EXTENSIONS = {ArtifactKind.GCODE: "gcode", ArtifactKind.THREE_MF: "3mf"}


@dataclass(frozen=True, slots=True)
class ChunkReceipt:
    complete: bool
    received: int
    artifact: ArtifactDTO | None


class ArtifactService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        signals: CallSignals,
        clock: Clock,
        ids: IdGenerator,
        config: AgentConfig,
    ) -> None:
        self._uow_factory = uow_factory
        self._signals = signals
        self._clock = clock
        self._ids = ids
        self._config = config

    async def put_chunk(
        self,
        instance_id: str,
        run_id: str,
        *,
        kind: str,
        scene_version: int,
        chunk_index: int,
        chunk_count: int,
        sha256: str,
        data: bytes,
        scene_epoch: str = "",
    ) -> ChunkReceipt:
        artifact_kind = parse_kind(kind)
        verify_chunk_plan(chunk_index, chunk_count)
        if len(sha256) != 64:
            raise InvalidArtifact("sha256 must be the hex digest of the whole artifact")
        async with self._uow_factory() as uow:
            run = await uow.runs.get(run_id)
            if run is None or run.instance_id != instance_id:
                raise NotFound()
            instance = await uow.instances.get(instance_id)
            if run.state is RunState.ABORTED:
                raise InvalidArtifact("Run was cancelled")
            if instance is None or instance.scene_epoch != scene_epoch:
                raise InvalidArtifact("Artifact belongs to another slicer session")
            await uow.artifacts.lock(run_id, kind, scene_version, scene_epoch)
            await uow.artifacts.put_chunk(
                ArtifactChunk(
                    run_id=run_id,
                    kind=kind,
                    scene_version=scene_version,
                    scene_epoch=scene_epoch,
                    chunk_index=chunk_index,
                    chunk_count=chunk_count,
                    sha256=sha256.lower(),
                    data=data,
                ),
                self._clock.now(),
            )
            chunks = await uow.artifacts.list_chunks(run_id, kind, scene_version, scene_epoch)
            total = sum(len(chunk.data) for chunk in chunks)
            if total > self._config.max_artifact_bytes:
                raise PayloadTooLarge()
            if len(chunks) < chunk_count:
                await uow.commit()
                return ChunkReceipt(complete=False, received=len(chunks), artifact=None)
            assembled = b"".join(chunk.data for chunk in chunks)
            digests = {chunk.sha256 for chunk in chunks}
            if len(digests) != 1 or any(chunk.chunk_count != chunk_count for chunk in chunks):
                raise InvalidArtifact("Chunks disagree about the artifact")
            digest = verify_sha256(digests.pop(), assembled)
            meta = ArtifactDTO(
                id=self._ids.new_id(),
                run_id=run_id,
                kind=kind,
                scene_version=scene_version,
                scene_epoch=scene_epoch,
                name=f"{run_id}-v{scene_version}.{EXTENSIONS[artifact_kind]}",
                content_type=CONTENT_TYPES[artifact_kind],
                size=len(assembled),
                sha256=digest,
                created_at=self._clock.now(),
            )
            await uow.artifacts.save(ArtifactBlob(meta=meta, data=assembled))
            await uow.artifacts.delete_chunks(run_id, kind, scene_version, scene_epoch)
            await uow.commit()
        self._signals.notify(f"artifacts:{run_id}")
        return ChunkReceipt(complete=True, received=chunk_count, artifact=meta)

    async def get(self, instance_id: str, run_id: str, kind: str) -> ArtifactBlob:
        parse_kind(kind)
        async with self._uow_factory() as uow:
            run = await uow.runs.get(run_id)
            if run is None or run.instance_id != instance_id:
                raise NotFound()
            blob = await uow.artifacts.get_latest(run_id, kind)
        if blob is None:
            raise NotFound("Artifact has not been saved")
        return blob

    async def list(self, instance_id: str, run_id: str) -> list[ArtifactDTO]:
        async with self._uow_factory() as uow:
            run = await uow.runs.get(run_id)
            if run is None or run.instance_id != instance_id:
                raise NotFound()
            return await uow.artifacts.list_meta(run_id)
