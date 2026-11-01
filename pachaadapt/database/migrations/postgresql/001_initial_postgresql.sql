-- Esquema equivalente para PostgreSQL 15+. Aplicar en orden de migración.
CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, display_name TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('student','teacher','admin')), active BOOLEAN NOT NULL DEFAULT TRUE);
CREATE TABLE IF NOT EXISTS assignments(
 id TEXT PRIMARY KEY, classroom_id TEXT, title VARCHAR(200) NOT NULL, instructions TEXT NOT NULL DEFAULT '',
 due_at TIMESTAMPTZ, created_by TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('draft','published','closed')),
 version INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE TABLE IF NOT EXISTS submissions(
 id TEXT PRIMARY KEY, assignment_id TEXT NOT NULL REFERENCES assignments(id) ON DELETE CASCADE, student_id TEXT NOT NULL,
 answer TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'submitted' CHECK(status IN ('submitted','reviewed','returned')),
 client_updated_at TIMESTAMPTZ, server_version INTEGER NOT NULL DEFAULT 1, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), UNIQUE(assignment_id,student_id));
CREATE TABLE IF NOT EXISTS sync_operations(
 operation_id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
 payload_hash TEXT NOT NULL, result_json JSONB NOT NULL, received_at TIMESTAMPTZ NOT NULL DEFAULT now());
CREATE INDEX IF NOT EXISTS idx_assignments_classroom ON assignments(classroom_id);
CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX IF NOT EXISTS idx_submissions_student ON submissions(student_id);
CREATE INDEX IF NOT EXISTS idx_sync_received ON sync_operations(received_at);

-- Registro de versión de migración.
INSERT INTO schema_migrations(version) VALUES (1) ON CONFLICT (version) DO NOTHING;
