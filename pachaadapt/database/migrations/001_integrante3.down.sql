-- REVERSIÓN MANUAL de 001 (DESTRUCTIVA: borra datos del integrante 3). El módulo NUNCA la ejecuta.
-- Revisar y respaldar antes de ejecutar a mano.
DROP TABLE IF EXISTS i3_messages;
DROP TABLE IF EXISTS i3_conversations;
DROP TABLE IF EXISTS i3_document_versions;
DROP TABLE IF EXISTS i3_documents;
DROP TABLE IF EXISTS i3_teacher_preferences;
DROP TABLE IF EXISTS i3_reports;
DELETE FROM i3_schema_migrations WHERE version = '001_integrante3';
