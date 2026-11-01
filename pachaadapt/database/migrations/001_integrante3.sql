-- Migración incremental 001 (INTEGRANTE 3). Solo CREATE ... IF NOT EXISTS; no toca tablas ajenas.
-- Prefijo i3_ para evitar colisiones con el esquema compartido futuro. SQL portable (SQLite/MariaDB con ajustes menores).

CREATE TABLE IF NOT EXISTS i3_teacher_preferences (
    teacher_id  TEXT PRIMARY KEY,
    prefs_json  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS i3_documents (
    id                 TEXT PRIMARY KEY,
    owner_id           TEXT NOT NULL,
    title              TEXT NOT NULL,
    source_material_id TEXT,                       -- referencia opcional al material del integrante 2
    original_content   TEXT NOT NULL,              -- inmutable: nunca se actualiza
    current_version    INTEGER NOT NULL CHECK (current_version >= 1),
    archived           INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0,1)),
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_i3_documents_owner ON i3_documents(owner_id, archived);

CREATE TABLE IF NOT EXISTS i3_document_versions (
    document_id    TEXT NOT NULL REFERENCES i3_documents(id),
    version        INTEGER NOT NULL CHECK (version >= 1),
    content        TEXT NOT NULL,
    author_id      TEXT NOT NULL,
    reason         TEXT NOT NULL DEFAULT '',
    restored_from  INTEGER,                         -- versión de origen si es una restauración
    created_at     TEXT NOT NULL,
    PRIMARY KEY (document_id, version)              -- impide versiones duplicadas
);

CREATE TABLE IF NOT EXISTS i3_conversations (
    id          TEXT PRIMARY KEY,
    teacher_id  TEXT NOT NULL,
    document_id TEXT REFERENCES i3_documents(id),
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_i3_conversations_teacher ON i3_conversations(teacher_id);

CREATE TABLE IF NOT EXISTS i3_messages (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id  TEXT NOT NULL REFERENCES i3_conversations(id),
    role             TEXT NOT NULL CHECK (role IN ('user','assistant')),
    content          TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_i3_messages_conv ON i3_messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS i3_reports (
    id           TEXT PRIMARY KEY,
    teacher_id   TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    status       TEXT NOT NULL,
    criteria_json TEXT NOT NULL,                    -- criterios usados (reproducibilidad)
    report_json  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_i3_reports_teacher ON i3_reports(teacher_id, created_at);
