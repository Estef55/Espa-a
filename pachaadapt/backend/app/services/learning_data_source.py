"""Fuente de resultados autorizados para informes agregados.

Solo entrega resultados revisados explícitamente, validados y puntuados. Nunca
convierte respuestas pendientes/rechazadas en calificaciones. El ámbito se limita
a aulas cuyo docente propietario coincide con el solicitante.
"""
from __future__ import annotations

import hashlib
from contextlib import closing
from typing import Sequence

from ai.learning_analysis.result_analyzer import LearningRecord
from app.db import connect


class SQLiteLearningDataSource:
    def fetch_records(self, teacher_id: str, filters: dict) -> Sequence[LearningRecord]:
        with closing(connect()) as con:
            teacher_row = con.execute("SELECT is_demo FROM users WHERE id=?", (teacher_id,)).fetchone()
        demo_scope = bool(teacher_row["is_demo"]) if teacher_row else False
        clauses = [
            "(c.teacher_id = ? OR (a.classroom_id IS NULL AND a.created_by = ?))",
            "(c.is_demo = ? OR (a.classroom_id IS NULL AND a.is_demo = ?))",
            "s.is_demo = ?",
            "s.status = 'reviewed'",
            "s.validation_status = 'validated'",
            "s.score IS NOT NULL",
            "s.max_score IS NOT NULL",
            "s.max_score > 0",
            "s.score >= 0",
            "s.score <= s.max_score",
            "s.reviewed_at IS NOT NULL",
            "a.is_demo = ?",
        ]
        params: list[object] = [teacher_id, teacher_id, int(demo_scope), int(demo_scope),
                                int(demo_scope), int(demo_scope)]
        if filters.get("group"):
            clauses.append("c.name = ?")
            params.append(filters["group"])
        if filters.get("date_from"):
            clauses.append("s.reviewed_at >= ?")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            # The report service applies the final date filter too; this predicate
            # is deliberately omitted for date-only upper bounds to include the day.
            if len(filters["date_to"]) > 10:
                clauses.append("s.reviewed_at <= ?")
                params.append(filters["date_to"])

        sql = """
            SELECT s.student_id, s.score, s.max_score, s.reviewed_at,
                   a.title AS assignment_title, c.name AS classroom_name,
                   m.title AS material_title
            FROM submissions s
            JOIN assignments a ON a.id = s.assignment_id
            LEFT JOIN classrooms c ON c.id = a.classroom_id
            LEFT JOIN materials m ON m.id = a.material_id
            WHERE """ + " AND ".join(clauses) + """
            ORDER BY s.reviewed_at, s.id
        """
        with closing(connect()) as con:
            rows = con.execute(sql, params).fetchall()

        records = []
        for row in rows:
            topic = (row["material_title"] or row["assignment_title"] or "").strip()
            # Opaque, stable reference for aggregation; no names or raw IDs leave DB.
            student_ref = hashlib.sha256(
                f"{teacher_id}:{row['student_id']}".encode("utf-8")
            ).hexdigest()[:24]
            records.append(LearningRecord(
                student_ref=student_ref,
                topic=topic,
                score=float(row["score"]),
                max_score=float(row["max_score"]),
                recorded_at=row["reviewed_at"],
                group=row["classroom_name"],
            ))
        if filters.get("topic"):
            records = [r for r in records if r.topic == filters["topic"]]
        return records
