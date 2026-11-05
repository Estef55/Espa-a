-- Resultados trazables, aulas y aislamiento explícito de datos de demostración.
-- Todas las columnas nuevas son aditivas; registros históricos quedan como no demo y sin calificación validada.
CREATE TABLE IF NOT EXISTS classrooms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    teacher_id TEXT NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(teacher_id, name, is_demo)
);
CREATE INDEX IF NOT EXISTS idx_classrooms_teacher ON classrooms(teacher_id, is_demo);
CREATE TABLE IF NOT EXISTS classroom_members (
    classroom_id TEXT NOT NULL REFERENCES classrooms(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    member_role TEXT NOT NULL CHECK(member_role IN ('student','teacher')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(classroom_id,user_id)
);
ALTER TABLE users ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1));
ALTER TABLE assignments ADD COLUMN material_id TEXT;
ALTER TABLE assignments ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1));
ALTER TABLE submissions ADD COLUMN score REAL;
ALTER TABLE submissions ADD COLUMN max_score REAL;
ALTER TABLE submissions ADD COLUMN validation_status TEXT NOT NULL DEFAULT 'pending'
    CHECK(validation_status IN ('pending','validated','rejected'));
ALTER TABLE submissions ADD COLUMN reviewed_at TEXT;
ALTER TABLE submissions ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1));
ALTER TABLE materials ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1));
CREATE INDEX IF NOT EXISTS idx_submissions_valid_results
    ON submissions(status, validation_status, reviewed_at);
CREATE INDEX IF NOT EXISTS idx_assignments_material ON assignments(material_id);
