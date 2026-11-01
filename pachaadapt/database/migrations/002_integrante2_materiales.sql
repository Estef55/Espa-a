-- Persistencia del integrante 2 en la misma base SQLite provisional del proyecto.
-- Los binarios originales permanecen en almacenamiento local; metadatos y texto extraído, en DB.
CREATE TABLE IF NOT EXISTS i2_materials (
    id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    size INTEGER NOT NULL CHECK (size >= 0),
    sha256 TEXT NOT NULL,
    original_path TEXT NOT NULL,
    extracted_text TEXT,
    extracted_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_i2_materials_owner ON i2_materials(owner_id, created_at);
