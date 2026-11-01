"""Historial de cambios y versiones de los documentos editables.

- Control optimista: cada escritura exige ``expected_version``; si otra edición se
  adelantó se lanza Conflict (409) en lugar de sobrescribir en silencio.
- Restaurar crea una versión NUEVA con el contenido antiguo (el historial posterior se conserva).
- Las versiones solo se añaden; nunca se modifican ni se borran.
- Cada versión registra número, fecha, autor y motivo.
"""
from __future__ import annotations

from ai.assistant.document_builder import (check_content, check_expected, check_reason, doc_dict,
                                           load_owned)
from ai.errors import Conflict, NotFound, ValidationError
from ai.storage import Database, now_iso


class RevisionManager:
    def __init__(self, db: Database):
        self.db = db

    def versions(self, owner_id: str, document_id: str) -> list[dict]:
        with self.db.read() as conn:
            load_owned(conn, document_id, owner_id)
            rows = conn.execute(
                "SELECT version, author_id, reason, restored_from, created_at, LENGTH(content) AS size "
                "FROM i3_document_versions WHERE document_id = ? ORDER BY version DESC", (document_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_version(self, owner_id: str, document_id: str, version: int) -> dict:
        with self.db.read() as conn:
            load_owned(conn, document_id, owner_id)
            row = conn.execute(
                "SELECT version, content, author_id, reason, restored_from, created_at "
                "FROM i3_document_versions WHERE document_id = ? AND version = ?", (document_id, version)
            ).fetchone()
        if row is None:
            raise NotFound("Versión no encontrada.")
        return dict(row)

    def _append_version(self, conn, row, owner_id, new_content, reason, expected, restored_from=None) -> int:
        if row["archived"]:
            raise ValidationError("El documento está archivado; no admite cambios.")
        if expected != row["current_version"]:
            raise Conflict("El documento cambió desde la versión que usted tenía. Recárguelo.",
                           current_version=row["current_version"], expected_version=expected)
        latest = conn.execute("SELECT content FROM i3_document_versions WHERE document_id=? AND version=?",
                              (row["id"], row["current_version"])).fetchone()["content"]
        if new_content == latest:
            raise ValidationError("No hay cambios respecto a la versión actual.")
        new_version, ts = row["current_version"] + 1, now_iso()
        conn.execute(
            "INSERT INTO i3_document_versions(document_id, version, content, author_id, reason, "
            "restored_from, created_at) VALUES (?,?,?,?,?,?,?)",
            (row["id"], new_version, new_content, owner_id, reason, restored_from, ts))
        cur = conn.execute(
            "UPDATE i3_documents SET current_version=?, updated_at=? WHERE id=? AND current_version=?",
            (new_version, ts, row["id"], row["current_version"]))
        if cur.rowcount != 1:  # defensa adicional; BEGIN IMMEDIATE ya serializa
            raise Conflict("Edición concurrente detectada.", current_version=row["current_version"])
        return new_version

    def _current(self, owner_id: str, document_id: str) -> dict:
        with self.db.read() as conn:
            row = load_owned(conn, document_id, owner_id)
            content = conn.execute("SELECT content FROM i3_document_versions WHERE document_id=? AND version=?",
                                   (document_id, row["current_version"])).fetchone()["content"]
        return {**doc_dict(row), "content": content}

    def save(self, owner_id: str, document_id: str, content, expected_version, reason=None) -> dict:
        content, reason, expected = check_content(content), check_reason(reason), check_expected(expected_version)
        with self.db.transaction() as conn:
            row = load_owned(conn, document_id, owner_id)
            self._append_version(conn, row, owner_id, content, reason, expected)
        return self._current(owner_id, document_id)

    def restore(self, owner_id: str, document_id: str, version, expected_version, reason=None) -> dict:
        expected = check_expected(expected_version)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValidationError("version debe ser un entero >= 1.")
        reason = check_reason(reason) or f"Restauración de la versión {version}"
        with self.db.transaction() as conn:
            row = load_owned(conn, document_id, owner_id)
            target = conn.execute(
                "SELECT content FROM i3_document_versions WHERE document_id=? AND version=?",
                (document_id, version)).fetchone()
            if target is None:
                raise NotFound("Versión no encontrada.")
            self._append_version(conn, row, owner_id, target["content"], reason, expected, restored_from=version)
        return self._current(owner_id, document_id)
