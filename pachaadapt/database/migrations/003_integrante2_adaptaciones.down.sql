-- REVERSIÓN MANUAL DESTRUCTIVA: elimina estados, adaptaciones y vínculos (no los archivos originales ni i2_materials).
-- Respaldar la base de datos antes de ejecutar.
DROP TABLE IF EXISTS i2_adaptation_links;
DROP INDEX IF EXISTS ix_i2_adaptations_material;
DROP TABLE IF EXISTS i2_adaptations;
DROP TABLE IF EXISTS i2_material_state;
DELETE FROM i3_schema_migrations WHERE version = '003_integrante2_adaptaciones';
