-- Migración 003 (INTEGRANTE 2): estado de procesamiento, adaptaciones persistidas y vínculos.
-- Solo CREATE ... IF NOT EXISTS; no modifica i2_materials ni tablas de otros integrantes.
-- Los archivos binarios (original, audio) siguen en storage/materials/; aquí van metadatos y texto.

CREATE TABLE IF NOT EXISTS i2_material_state (
    material_id   TEXT PRIMARY KEY REFERENCES i2_materials(id),
    status        TEXT NOT NULL DEFAULT 'uploaded'
                  CHECK (status IN ('uploaded','extracted','no_text','failed')),
    method        TEXT,                              -- txt | pdf_text | ocr
    error_code    TEXT,                              -- invalid_document | engine_unavailable | original_missing | processing_error
    error_message TEXT,
    attempts      INTEGER NOT NULL DEFAULT 0,        -- intentos de extracción (reintentos)
    page_count    INTEGER,
    image_count   INTEGER,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    is_demo       INTEGER NOT NULL DEFAULT 0 CHECK (is_demo IN (0,1)),
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS i2_adaptations (
    id            TEXT PRIMARY KEY,
    material_id   TEXT NOT NULL REFERENCES i2_materials(id),   -- relación con el original
    kind          TEXT NOT NULL,                                -- summary|easy_read|quiz|outline|image_notes|audio
    status        TEXT NOT NULL CHECK (status IN ('complete','partial')),
    options_json  TEXT NOT NULL DEFAULT '{}',
    content_json  TEXT NOT NULL,
    content_text  TEXT NOT NULL,
    warnings_json TEXT NOT NULL DEFAULT '[]',
    source_sha256 TEXT NOT NULL,
    source_origin TEXT NOT NULL CHECK (source_origin IN ('extracted','edited')),
    generator     TEXT NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','approved')),
    reviewed_by   TEXT,
    reviewed_at   TEXT,
    created_by    TEXT NOT NULL,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_i2_adaptations_material ON i2_adaptations(material_id, created_at);

-- Relación adaptación → documento editable (i3_documents) o actividad (assignments).
-- Sin clave foránea al destino (pertenece a otros módulos): el servicio valida existencia y dueño.
CREATE TABLE IF NOT EXISTS i2_adaptation_links (
    adaptation_id TEXT NOT NULL REFERENCES i2_adaptations(id),
    target_type   TEXT NOT NULL CHECK (target_type IN ('document','assignment')),
    target_id     TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    PRIMARY KEY (adaptation_id, target_type, target_id)
);
