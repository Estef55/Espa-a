CREATE TABLE IF NOT EXISTS materials (
 id TEXT PRIMARY KEY,
 title VARCHAR(200) NOT NULL,
 description TEXT NOT NULL DEFAULT '',
 resource_url TEXT NOT NULL,
 mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
 created_by TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('draft','published')),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_materials_status ON materials(status,created_at);
CREATE INDEX IF NOT EXISTS idx_materials_creator ON materials(created_by);

-- Registro de versión de migración.
INSERT INTO schema_migrations(version) VALUES (3) ON CONFLICT (version) DO NOTHING;
