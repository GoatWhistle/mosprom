-- migrate:up
ALTER TABLE instances ADD COLUMN scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE state_snapshots ADD COLUMN scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE change_batches ADD COLUMN scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE tool_calls ADD COLUMN scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE slice_jobs ADD COLUMN scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE artifacts ADD COLUMN scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE artifact_chunks ADD COLUMN scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE tool_calls ADD COLUMN expected_scene_epoch text NOT NULL DEFAULT '';
ALTER TABLE artifacts DROP CONSTRAINT artifacts_run_kind_scene_key;
ALTER TABLE artifacts ADD CONSTRAINT artifacts_run_kind_scene_key UNIQUE (run_id, kind, scene_epoch, scene_version);
ALTER TABLE artifact_chunks DROP CONSTRAINT artifact_chunks_pkey;
ALTER TABLE artifact_chunks ADD PRIMARY KEY (run_id, kind, scene_epoch, scene_version, chunk_index);

-- migrate:down
ALTER TABLE artifacts DROP CONSTRAINT artifacts_run_kind_scene_key;
ALTER TABLE artifact_chunks DROP CONSTRAINT artifact_chunks_pkey;
ALTER TABLE instances DROP COLUMN scene_epoch;
ALTER TABLE state_snapshots DROP COLUMN scene_epoch;
ALTER TABLE change_batches DROP COLUMN scene_epoch;
ALTER TABLE tool_calls DROP COLUMN scene_epoch;
ALTER TABLE slice_jobs DROP COLUMN scene_epoch;
ALTER TABLE artifacts DROP COLUMN scene_epoch;
ALTER TABLE artifact_chunks DROP COLUMN scene_epoch;
ALTER TABLE tool_calls DROP COLUMN expected_scene_epoch;
ALTER TABLE artifacts ADD CONSTRAINT artifacts_run_kind_scene_key UNIQUE (run_id, kind, scene_version);
ALTER TABLE artifact_chunks ADD PRIMARY KEY (run_id, kind, scene_version, chunk_index);
