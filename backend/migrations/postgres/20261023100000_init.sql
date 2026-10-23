-- migrate:up
CREATE TABLE instances (
    id text PRIMARY KEY,
    token_hash text NOT NULL,
    slicer_version text,
    printer jsonb NOT NULL DEFAULT '{}'::jsonb,
    modes jsonb NOT NULL DEFAULT '[]'::jsonb,
    contract_version text,
    scene_version integer NOT NULL DEFAULT 0,
    state jsonb NOT NULL DEFAULT '{}'::jsonb,
    registered_at timestamptz NOT NULL,
    last_seen_at timestamptz,
    CONSTRAINT instances_token_hash_key UNIQUE (token_hash),
    CONSTRAINT instances_scene_version_check CHECK (scene_version >= 0)
);

CREATE TABLE state_snapshots (
    id bigserial PRIMARY KEY,
    instance_id text NOT NULL REFERENCES instances (id),
    scene_version integer NOT NULL,
    state jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX state_snapshots_instance_idx ON state_snapshots (instance_id, id DESC);

CREATE TABLE conversations (
    id uuid PRIMARY KEY,
    instance_id text NOT NULL REFERENCES instances (id),
    title text NOT NULL,
    mode text NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT conversations_mode_check CHECK (mode IN ('auto', 'ask'))
);
CREATE INDEX conversations_instance_idx ON conversations (instance_id, created_at DESC, id DESC);

CREATE TABLE attachments (
    id uuid PRIMARY KEY,
    instance_id text NOT NULL REFERENCES instances (id),
    conversation_id uuid REFERENCES conversations (id),
    source text NOT NULL,
    name text NOT NULL,
    content_type text NOT NULL,
    size bigint NOT NULL,
    sha256 text NOT NULL,
    data bytea NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT attachments_source_check CHECK (source IN ('user', 'render')),
    CONSTRAINT attachments_size_check CHECK (size = octet_length(data))
);
CREATE INDEX attachments_conversation_idx ON attachments (conversation_id);

CREATE TABLE runs (
    id uuid PRIMARY KEY,
    conversation_id uuid NOT NULL REFERENCES conversations (id),
    instance_id text NOT NULL REFERENCES instances (id),
    state text NOT NULL,
    requirements_ready boolean NOT NULL DEFAULT false,
    requirements_summary text,
    correction_key text,
    correction_failures integer NOT NULL DEFAULT 0,
    help_required boolean NOT NULL DEFAULT false,
    steps integer NOT NULL DEFAULT 0,
    last_error text,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    finished_at timestamptz,
    CONSTRAINT runs_state_check CHECK (state IN (
        'interviewing', 'agent_working', 'awaiting_user', 'awaiting_confirmation',
        'executing_tool', 'slicing', 'saving', 'completed', 'failed', 'aborted'
    ))
);
CREATE UNIQUE INDEX runs_one_active_per_instance
    ON runs (instance_id) WHERE state NOT IN ('completed', 'failed', 'aborted');
CREATE INDEX runs_conversation_idx ON runs (conversation_id, created_at);

CREATE TABLE messages (
    seq bigserial PRIMARY KEY,
    id uuid NOT NULL,
    conversation_id uuid NOT NULL REFERENCES conversations (id),
    run_id uuid REFERENCES runs (id),
    role text NOT NULL,
    content text NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT messages_id_key UNIQUE (id),
    CONSTRAINT messages_role_check CHECK (role IN ('user', 'assistant'))
);
CREATE INDEX messages_conversation_idx ON messages (conversation_id, seq);

CREATE TABLE message_attachments (
    message_id uuid NOT NULL REFERENCES messages (id),
    attachment_id uuid NOT NULL REFERENCES attachments (id),
    position integer NOT NULL,
    PRIMARY KEY (message_id, attachment_id)
);

CREATE TABLE run_transitions (
    id bigserial PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    from_state text NOT NULL,
    to_state text NOT NULL,
    reason text NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX run_transitions_run_idx ON run_transitions (run_id, id);

CREATE TABLE run_events (
    id bigserial PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    conversation_id uuid NOT NULL REFERENCES conversations (id),
    kind text NOT NULL,
    payload jsonb NOT NULL,
    created_at timestamptz NOT NULL
);
CREATE INDEX run_events_run_idx ON run_events (run_id, id);

CREATE TABLE agent_transcript (
    id bigserial PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    entry jsonb NOT NULL
);
CREATE INDEX agent_transcript_run_idx ON agent_transcript (run_id, id);

CREATE TABLE requirement_batches (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    call_id text NOT NULL,
    questions jsonb NOT NULL,
    answer text,
    created_at timestamptz NOT NULL,
    answered_at timestamptz
);
CREATE INDEX requirement_batches_run_idx ON requirement_batches (run_id, created_at);

CREATE TABLE change_batches (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    call_id text NOT NULL,
    content_hash text NOT NULL,
    scene_version integer NOT NULL,
    operations jsonb NOT NULL,
    explanation text NOT NULL,
    status text NOT NULL,
    decision_text text,
    created_at timestamptz NOT NULL,
    decided_at timestamptz,
    CONSTRAINT change_batches_status_check CHECK (status IN (
        'proposed', 'accepted', 'rejected', 'clarified', 'stale', 'executed'
    ))
);
CREATE INDEX change_batches_run_idx ON change_batches (run_id, created_at);

CREATE TABLE tool_calls (
    call_id text PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    llm_call_id text NOT NULL,
    tool text NOT NULL,
    arguments jsonb NOT NULL,
    expected_scene_version integer NOT NULL,
    status text NOT NULL,
    batch_id uuid REFERENCES change_batches (id),
    result jsonb,
    error jsonb,
    applied jsonb NOT NULL DEFAULT '[]'::jsonb,
    scene_version integer,
    created_at timestamptz NOT NULL,
    sent_at timestamptz,
    finished_at timestamptz,
    CONSTRAINT tool_calls_status_check CHECK (status IN (
        'pending', 'sent', 'completed', 'failed', 'outcome_unknown'
    ))
);
CREATE INDEX tool_calls_run_idx ON tool_calls (run_id, created_at);
CREATE INDEX tool_calls_unfinished_idx ON tool_calls (run_id) WHERE status IN ('pending', 'sent');

CREATE TABLE slice_jobs (
    id bigserial PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    call_id text NOT NULL REFERENCES tool_calls (call_id),
    scene_version integer NOT NULL,
    status text NOT NULL,
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL,
    CONSTRAINT slice_jobs_call_key UNIQUE (call_id)
);

CREATE TABLE artifacts (
    id uuid PRIMARY KEY,
    run_id uuid NOT NULL REFERENCES runs (id),
    kind text NOT NULL,
    scene_version integer NOT NULL,
    name text NOT NULL,
    content_type text NOT NULL,
    size bigint NOT NULL,
    sha256 text NOT NULL,
    data bytea NOT NULL,
    created_at timestamptz NOT NULL,
    CONSTRAINT artifacts_kind_check CHECK (kind IN ('gcode', '3mf')),
    CONSTRAINT artifacts_run_kind_scene_key UNIQUE (run_id, kind, scene_version),
    CONSTRAINT artifacts_size_check CHECK (size = octet_length(data))
);

CREATE TABLE artifact_chunks (
    run_id uuid NOT NULL REFERENCES runs (id),
    kind text NOT NULL,
    scene_version integer NOT NULL,
    chunk_index integer NOT NULL,
    chunk_count integer NOT NULL,
    sha256 text NOT NULL,
    data bytea NOT NULL,
    created_at timestamptz NOT NULL,
    PRIMARY KEY (run_id, kind, scene_version, chunk_index),
    CONSTRAINT artifact_chunks_kind_check CHECK (kind IN ('gcode', '3mf')),
    CONSTRAINT artifact_chunks_index_check CHECK (chunk_index >= 0 AND chunk_index < chunk_count)
);

-- migrate:down
DROP TABLE artifact_chunks;
DROP TABLE artifacts;
DROP TABLE slice_jobs;
DROP TABLE tool_calls;
DROP TABLE change_batches;
DROP TABLE requirement_batches;
DROP TABLE agent_transcript;
DROP TABLE run_events;
DROP TABLE run_transitions;
DROP TABLE message_attachments;
DROP TABLE messages;
DROP TABLE runs;
DROP TABLE attachments;
DROP TABLE conversations;
DROP TABLE state_snapshots;
DROP TABLE instances;
