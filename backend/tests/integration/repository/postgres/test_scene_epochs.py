import hashlib
from datetime import timedelta

import pytest
from tests.integration.repository.postgres.test_repositories import INSTANCE, NOW, RUN, seed

from app.repository.postgres.pool import PostgresUnitOfWorkFactory
from app.usecase.dto.artifact import ArtifactBlob, ArtifactChunk, ArtifactDTO

pytestmark = pytest.mark.integration


async def test_new_epoch_accepts_reset_counter_and_rejects_old_snapshot(
    uow_factory: PostgresUnitOfWorkFactory,
) -> None:
    await seed(uow_factory)
    async with uow_factory() as uow:
        for epoch, version in [("old", 20), ("new", 1)]:
            await uow.instances.record_hello(
                INSTANCE,
                slicer_version="7",
                modes=["classic"],
                printer={},
                contract_version="2",
                now=NOW,
                scene_epoch=epoch,
            )
            assert await uow.instances.record_snapshot(
                INSTANCE, version, {"epoch": epoch}, NOW, epoch
            )
        assert not await uow.instances.record_snapshot(INSTANCE, 100, {"epoch": "old"}, NOW, "old")
        await uow.instances.advance_scene_version(INSTANCE, 100, "old")
        await uow.commit()
    async with uow_factory() as uow:
        instance = await uow.instances.get(INSTANCE)
        assert instance is not None
        assert (instance.scene_epoch, instance.scene_version) == ("new", 1)
        assert instance.state == {"epoch": "new"}


async def test_legacy_and_new_artifacts_with_same_counter_are_preserved(
    uow_factory: PostgresUnitOfWorkFactory,
) -> None:
    await seed(uow_factory)
    async with uow_factory() as uow:
        for index, epoch in enumerate(["", "new"]):
            data = str(index).encode()
            meta = ArtifactDTO(
                id=f"5555555{index}-5555-5555-5555-555555555555",
                run_id=RUN,
                kind="gcode",
                scene_version=1,
                scene_epoch=epoch,
                name="result.gcode",
                content_type="text/plain",
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
                created_at=NOW + timedelta(seconds=index),
            )
            await uow.artifacts.save(ArtifactBlob(meta=meta, data=data))
            await uow.artifacts.put_chunk(
                ArtifactChunk(
                    run_id=RUN,
                    kind="gcode",
                    scene_version=1,
                    scene_epoch=epoch,
                    chunk_index=0,
                    chunk_count=1,
                    sha256=meta.sha256,
                    data=data,
                ),
                NOW,
            )
        await uow.commit()
    async with uow_factory() as uow:
        assert len(await uow.artifacts.list_meta(RUN)) == 2
        latest = await uow.artifacts.get_latest(RUN, "gcode")
        assert latest is not None and latest.data == b"1"
        assert (await uow.artifacts.list_chunks(RUN, "gcode", 1, ""))[0].data == b"0"
        assert (await uow.artifacts.list_chunks(RUN, "gcode", 1, "new"))[0].data == b"1"
