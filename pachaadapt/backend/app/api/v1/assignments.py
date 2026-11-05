from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from app.db import connect, transaction
from app.core.security import current_actor, require_roles
from app.core.logging import log_event

router = APIRouter(prefix="/assignments", tags=["assignments"])

class AssignmentIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    instructions: str = Field(default="", max_length=10000)
    classroom_id: Optional[str] = None
    due_at: Optional[str] = None
    material_id: Optional[str] = None
    status: str = "published"

@router.post("", status_code=201)
def create_assignment(data: AssignmentIn, actor=Depends(current_actor)):
    require_roles(actor, "teacher", "admin")
    if data.status not in {"draft", "published", "closed"}:
        raise HTTPException(422, "Estado inválido")
    aid = str(uuid4())
    with transaction() as con:
        if data.classroom_id:
            classroom = con.execute("SELECT teacher_id,is_demo FROM classrooms WHERE id=?", (data.classroom_id,)).fetchone()
            if not classroom:
                raise HTTPException(404, "Aula no encontrada")
            if actor.role == "teacher" and classroom["teacher_id"] != actor.id:
                raise HTTPException(403, "El aula no pertenece al docente")
        if data.material_id:
            material = con.execute("SELECT created_by,is_demo FROM materials WHERE id=?", (data.material_id,)).fetchone()
            if not material:
                raise HTTPException(404, "Material no encontrado")
            if actor.role == "teacher" and material["created_by"] != actor.id:
                raise HTTPException(403, "El material no pertenece al docente")
        actor_row = con.execute("SELECT is_demo,active FROM users WHERE id=?", (actor.id,)).fetchone()
        if actor_row and not actor_row["active"]:
            raise HTTPException(403, "La cuenta docente está desactivada")
        is_demo = int(bool(actor_row["is_demo"])) if actor_row else 0
        if data.classroom_id and int(classroom["is_demo"]) != is_demo:
            raise HTTPException(409, "No se pueden mezclar aulas reales y de demostración")
        if data.material_id and int(material["is_demo"]) != is_demo:
            raise HTTPException(409, "No se pueden mezclar materiales reales y de demostración")
        con.execute("""INSERT INTO assignments(id,classroom_id,title,instructions,due_at,created_by,status,material_id,is_demo)
          VALUES(?,?,?,?,?,?,?,?,?)""", (aid,data.classroom_id,data.title.strip(),data.instructions,data.due_at,actor.id,data.status,data.material_id,is_demo))
        row = dict(con.execute("SELECT * FROM assignments WHERE id=?", (aid,)).fetchone())
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id) VALUES(?,?,?,?)",
                    (actor.id,"create","assignment",aid))
    log_event("assignment.created", actor_id=actor.id, assignment_id=aid)
    return row

@router.get("")
def list_assignments(classroom_id: Optional[str] = None, actor=Depends(current_actor)):
    con=connect()
    try:
        if actor.role == "student":
            rows=con.execute("""SELECT a.* FROM assignments a WHERE a.status='published'
                AND (? IS NULL OR a.classroom_id=?)
                AND (a.classroom_id IS NULL OR EXISTS (
                    SELECT 1 FROM classroom_members cm WHERE cm.classroom_id=a.classroom_id
                    AND cm.user_id=? AND cm.member_role='student'))
                ORDER BY a.created_at DESC""",(classroom_id,classroom_id,actor.id)).fetchall()
        else:
            rows=con.execute("""SELECT * FROM assignments WHERE (? IS NULL OR classroom_id=?)
                AND (? != 'teacher' OR created_by=?) ORDER BY created_at DESC""",
                (classroom_id,classroom_id,actor.role,actor.id)).fetchall()
        return [dict(r) for r in rows]
    finally: con.close()

@router.get("/{assignment_id}")
def get_assignment(assignment_id: str, actor=Depends(current_actor)):
    con=connect()
    try:
        row=con.execute("SELECT * FROM assignments WHERE id=?",(assignment_id,)).fetchone()
        if not row or (actor.role=="student" and (row["status"]!="published" or
            (row["classroom_id"] is not None and not con.execute(
                "SELECT 1 FROM classroom_members WHERE classroom_id=? AND user_id=? AND member_role='student'",
                (row["classroom_id"], actor.id)).fetchone()))) or (actor.role=="teacher" and row["created_by"] != actor.id):
            raise HTTPException(404,"Asignación no encontrada")
        return dict(row)
    finally: con.close()

@router.put("/{assignment_id}")
def update_assignment(assignment_id: str, data: AssignmentIn, expected_version: int = Query(ge=1), actor=Depends(current_actor)):
    require_roles(actor,"teacher","admin")
    if data.status not in {"draft","published","closed"}:
        raise HTTPException(422,"Estado inválido")
    with transaction() as con:
        existing=con.execute("SELECT created_by,is_demo FROM assignments WHERE id=?",(assignment_id,)).fetchone()
        if not existing:
            raise HTTPException(404,"Asignación no encontrada")
        if actor.role=="teacher" and existing["created_by"] != actor.id:
            raise HTTPException(403,"Solo puedes modificar tus propias actividades")
        if data.classroom_id:
            classroom = con.execute("SELECT teacher_id,is_demo FROM classrooms WHERE id=?", (data.classroom_id,)).fetchone()
            if not classroom or (actor.role == "teacher" and classroom["teacher_id"] != actor.id):
                raise HTTPException(404, "Aula no encontrada o no autorizada")
        if data.material_id:
            material = con.execute("SELECT created_by,is_demo FROM materials WHERE id=?", (data.material_id,)).fetchone()
            if not material or (actor.role == "teacher" and material["created_by"] != actor.id):
                raise HTTPException(404, "Material no encontrado o no autorizado")
        if data.classroom_id and int(classroom["is_demo"]) != int(existing["is_demo"]):
            raise HTTPException(409, "No se pueden mezclar aulas reales y de demostración")
        if data.material_id and int(material["is_demo"]) != int(existing["is_demo"]):
            raise HTTPException(409, "No se pueden mezclar materiales reales y de demostración")
        cur=con.execute("""UPDATE assignments SET title=?,instructions=?,classroom_id=?,due_at=?,status=?,material_id=?,
          version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND version=?""",
          (data.title.strip(),data.instructions,data.classroom_id,data.due_at,data.status,data.material_id,assignment_id,expected_version))
        if cur.rowcount==0:
            exists=con.execute("SELECT 1 FROM assignments WHERE id=?",(assignment_id,)).fetchone()
            raise HTTPException(409 if exists else 404,"Conflicto de versión" if exists else "Asignación no encontrada")
        row=dict(con.execute("SELECT * FROM assignments WHERE id=?",(assignment_id,)).fetchone())
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id) VALUES(?,?,?,?)",
                    (actor.id,"update","assignment",assignment_id))
    log_event("assignment.updated", actor_id=actor.id, assignment_id=assignment_id, version=row["version"])
    return row
