-- migrate:up
ALTER TABLE conversations ADD COLUMN project_state text NOT NULL DEFAULT 'none';
ALTER TABLE conversations ADD COLUMN project_version integer NOT NULL DEFAULT 0;
ALTER TABLE conversations ADD COLUMN project_sha256 text;
ALTER TABLE conversations ADD COLUMN project_saved_at timestamptz;
ALTER TABLE conversations ADD CONSTRAINT conversations_project_state_check CHECK (project_state IN ('none', 'saved', 'empty'));
ALTER TABLE instances ADD COLUMN active_conversation_id uuid REFERENCES conversations (id) ON DELETE SET NULL;
ALTER TABLE runs ADD COLUMN project_version integer NOT NULL DEFAULT 0;
ALTER TABLE messages ADD COLUMN client_message_id text;
CREATE UNIQUE INDEX messages_client_message_key ON messages (conversation_id, client_message_id) WHERE client_message_id IS NOT NULL;

-- migrate:down
DROP INDEX messages_client_message_key;
ALTER TABLE messages DROP COLUMN client_message_id;
ALTER TABLE runs DROP COLUMN project_version;
ALTER TABLE instances DROP COLUMN active_conversation_id;
ALTER TABLE conversations DROP CONSTRAINT conversations_project_state_check;
ALTER TABLE conversations DROP COLUMN project_saved_at;
ALTER TABLE conversations DROP COLUMN project_sha256;
ALTER TABLE conversations DROP COLUMN project_version;
ALTER TABLE conversations DROP COLUMN project_state;
