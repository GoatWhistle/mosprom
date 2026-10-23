from datetime import datetime

from psycopg import AsyncConnection

from app.usecase.dto.artifact import ArtifactBlob, ArtifactChunk, ArtifactDTO

META = "id, run_id, kind, scene_version, name, content_type, size, sha256, created_at, scene_epoch"
LOCK = "SELECT pg_advisory_xact_lock(hashtext(%(key)s))"
PUT_CHUNK = """
INSERT INTO artifact_chunks (run_id, kind, scene_version, chunk_index, chunk_count, sha256, data,
    created_at, scene_epoch)
VALUES (%(run_id)s, %(kind)s, %(scene_version)s, %(chunk_index)s, %(chunk_count)s, %(sha256)s,
    %(data)s, %(now)s, %(scene_epoch)s)
ON CONFLICT (run_id, kind, scene_epoch, scene_version, chunk_index) DO UPDATE
SET chunk_count = EXCLUDED.chunk_count, sha256 = EXCLUDED.sha256, data = EXCLUDED.data
"""
LIST_CHUNKS = """
SELECT run_id, kind, scene_version, chunk_index, chunk_count, sha256, data, scene_epoch FROM artifact_chunks
WHERE run_id = %(run_id)s AND kind = %(kind)s AND scene_version = %(scene_version)s AND scene_epoch = %(scene_epoch)s
ORDER BY chunk_index
"""
DELETE_CHUNKS = """
DELETE FROM artifact_chunks
WHERE run_id = %(run_id)s AND kind = %(kind)s AND scene_version = %(scene_version)s AND scene_epoch = %(scene_epoch)s
"""
SAVE = """
INSERT INTO artifacts (id, run_id, kind, scene_version, name, content_type, size, sha256, data,
    created_at, scene_epoch)
VALUES (%(id)s, %(run_id)s, %(kind)s, %(scene_version)s, %(name)s, %(content_type)s, %(size)s,
    %(sha256)s, %(data)s, %(created_at)s, %(scene_epoch)s)
ON CONFLICT ON CONSTRAINT artifacts_run_kind_scene_key DO UPDATE
SET name = EXCLUDED.name, content_type = EXCLUDED.content_type, size = EXCLUDED.size,
    sha256 = EXCLUDED.sha256, data = EXCLUDED.data
"""
GET_LATEST = f"""
SELECT {META}, data FROM artifacts WHERE run_id = %(run_id)s AND kind = %(kind)s
ORDER BY created_at DESC LIMIT 1
"""
LIST_META = f"SELECT {META} FROM artifacts WHERE run_id = %(run_id)s ORDER BY created_at, kind"


class PostgresArtifactRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def lock(self, run_id: str, kind: str, scene_version: int, scene_epoch: str = "") -> None:
        await self._connection.execute(
            LOCK, {"key": f"{run_id}:{kind}:{scene_epoch}:{scene_version}"}
        )

    async def put_chunk(self, chunk: ArtifactChunk, now: datetime) -> None:
        await self._connection.execute(
            PUT_CHUNK,
            {
                "run_id": chunk.run_id,
                "kind": chunk.kind,
                "scene_version": chunk.scene_version,
                "scene_epoch": chunk.scene_epoch,
                "chunk_index": chunk.chunk_index,
                "chunk_count": chunk.chunk_count,
                "sha256": chunk.sha256,
                "data": chunk.data,
                "now": now,
            },
        )

    async def list_chunks(
        self, run_id: str, kind: str, scene_version: int, scene_epoch: str = ""
    ) -> list[ArtifactChunk]:
        cursor = await self._connection.execute(
            LIST_CHUNKS,
            {
                "run_id": run_id,
                "kind": kind,
                "scene_version": scene_version,
                "scene_epoch": scene_epoch,
            },
        )
        return [
            ArtifactChunk(
                run_id=str(row[0]),
                kind=str(row[1]),
                scene_version=int(row[2]),
                chunk_index=int(row[3]),
                chunk_count=int(row[4]),
                sha256=str(row[5]),
                data=bytes(row[6]),
                scene_epoch=str(row[7]),
            )
            for row in await cursor.fetchall()
        ]

    async def delete_chunks(
        self, run_id: str, kind: str, scene_version: int, scene_epoch: str = ""
    ) -> None:
        await self._connection.execute(
            DELETE_CHUNKS,
            {
                "run_id": run_id,
                "kind": kind,
                "scene_version": scene_version,
                "scene_epoch": scene_epoch,
            },
        )

    async def save(self, blob: ArtifactBlob) -> None:
        meta = blob.meta
        await self._connection.execute(
            SAVE,
            {
                "id": meta.id,
                "run_id": meta.run_id,
                "kind": meta.kind,
                "scene_version": meta.scene_version,
                "scene_epoch": meta.scene_epoch,
                "name": meta.name,
                "content_type": meta.content_type,
                "size": meta.size,
                "sha256": meta.sha256,
                "data": blob.data,
                "created_at": meta.created_at,
            },
        )

    async def get_latest(self, run_id: str, kind: str) -> ArtifactBlob | None:
        cursor = await self._connection.execute(GET_LATEST, {"run_id": run_id, "kind": kind})
        row = await cursor.fetchone()
        if row is None:
            return None
        return ArtifactBlob(meta=_meta(row), data=bytes(row[10]))

    async def list_meta(self, run_id: str) -> list[ArtifactDTO]:
        cursor = await self._connection.execute(LIST_META, {"run_id": run_id})
        return [_meta(row) for row in await cursor.fetchall()]


def _meta(row: tuple[object, ...]) -> ArtifactDTO:
    assert isinstance(row[8], datetime)
    return ArtifactDTO(
        scene_epoch=str(row[9]),
        id=str(row[0]),
        run_id=str(row[1]),
        kind=str(row[2]),
        scene_version=int(str(row[3])),
        name=str(row[4]),
        content_type=str(row[5]),
        size=int(str(row[6])),
        sha256=str(row[7]),
        created_at=row[8],
    )
