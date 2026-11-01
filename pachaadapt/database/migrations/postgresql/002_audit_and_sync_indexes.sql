CREATE TABLE IF NOT EXISTS audit_log (
 id BIGSERIAL PRIMARY KEY,
 actor_id TEXT NOT NULL,
 action TEXT NOT NULL,
 entity_type TEXT NOT NULL,
 entity_id TEXT,
 details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor_id,created_at);
CREATE INDEX IF NOT EXISTS idx_sync_actor ON sync_operations(actor_id,received_at);

-- Registro de versión de migración.
INSERT INTO schema_migrations(version) VALUES (2) ON CONFLICT (version) DO NOTHING;
