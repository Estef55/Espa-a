"""Aulas y membresías con aislamiento por docente."""
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import Actor, current_actor, require_roles
from app.db import connect, transaction

router = APIRouter(prefix="/classrooms", tags=["classrooms"])


class ClassroomIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class MemberIn(BaseModel):
    user_id: str = Field(min_length=1, max_length=64)
    role: str = "student"


@router.post("", status_code=201)
def create_classroom(data: ClassroomIn, actor: Actor = Depends(current_actor)):
    require_roles(actor, "teacher", "admin")
    classroom_id = str(uuid4())
    with transaction() as con:
        teacher = con.execute("SELECT is_demo, active FROM users WHERE id=?", (actor.id,)).fetchone()
        if teacher and not teacher["active"]:
            raise HTTPException(403, "La cuenta docente está desactivada")
        is_demo = int(bool(teacher["is_demo"])) if teacher else 0
        con.execute("INSERT INTO classrooms(id,name,teacher_id,is_demo) VALUES(?,?,?,?)",
                    (classroom_id, data.name.strip(), actor.id, is_demo))
        con.execute("INSERT OR IGNORE INTO classroom_members(classroom_id,user_id,member_role) VALUES(?,?,?)",
                    (classroom_id, actor.id, "teacher"))
        row = dict(con.execute("SELECT * FROM classrooms WHERE id=?", (classroom_id,)).fetchone())
    return row


@router.get("")
def list_classrooms(actor: Actor = Depends(current_actor)):
    with connect() as con:
        if actor.role == "admin":
            rows = con.execute("SELECT * FROM classrooms ORDER BY created_at DESC").fetchall()
        elif actor.role == "teacher":
            rows = con.execute("SELECT * FROM classrooms WHERE teacher_id=? ORDER BY created_at DESC",
                               (actor.id,)).fetchall()
        else:
            rows = con.execute("""SELECT c.* FROM classrooms c JOIN classroom_members cm
                ON cm.classroom_id=c.id WHERE cm.user_id=? AND cm.member_role='student'
                ORDER BY c.created_at DESC""", (actor.id,)).fetchall()
        return [dict(r) for r in rows]


@router.post("/{classroom_id}/members", status_code=201)
def add_member(classroom_id: str, data: MemberIn, actor: Actor = Depends(current_actor)):
    require_roles(actor, "teacher", "admin")
    if data.role != "student":
        raise HTTPException(422, "Solo se pueden añadir estudiantes desde este endpoint")
    with transaction() as con:
        classroom = con.execute("SELECT teacher_id FROM classrooms WHERE id=?", (classroom_id,)).fetchone()
        if not classroom:
            raise HTTPException(404, "Aula no encontrada")
        if actor.role == "teacher" and classroom["teacher_id"] != actor.id:
            raise HTTPException(403, "El aula pertenece a otro docente")
        user = con.execute("SELECT role, active, is_demo FROM users WHERE id=?", (data.user_id,)).fetchone()
        if not user:
            raise HTTPException(404, "El estudiante debe existir antes de inscribirlo")
        if user["role"] != "student" or not user["active"]:
            raise HTTPException(409, "El usuario no es un estudiante activo")
        classroom_demo = con.execute("SELECT is_demo FROM classrooms WHERE id=?", (classroom_id,)).fetchone()["is_demo"]
        if int(user["is_demo"]) != int(classroom_demo):
            raise HTTPException(409, "No se pueden mezclar usuarios reales y de demostración")
        con.execute("INSERT OR IGNORE INTO classroom_members(classroom_id,user_id,member_role) VALUES(?,?,?)",
                    (classroom_id, data.user_id, "student"))
    return {"classroom_id": classroom_id, "user_id": data.user_id, "role": "student"}
