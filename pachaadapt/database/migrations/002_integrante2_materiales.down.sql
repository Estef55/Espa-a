-- REVERSIÓN MANUAL DESTRUCTIVA: elimina metadatos de materiales, no los archivos originales.
-- Respaldar la base de datos antes de ejecutar.
DROP INDEX IF EXISTS ix_i2_materials_owner;
DROP TABLE IF EXISTS i2_materials;
DELETE FROM i3_schema_migrations WHERE version = '002_integrante2_materiales';
