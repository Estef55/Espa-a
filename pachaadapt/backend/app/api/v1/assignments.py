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
    status: str = "published"

@router.post("", status_code=201)
def create_assignment(data: AssignmentIn, actor=Depends(current_actor)):
    require_roles(actor, "teacher", "admin")
    if data.status not in {"draft", "published", "closed"}:
        raise HTTPException(422, "Estado inválido")
    aid = str(uuid4())
    with transaction() as con:
        con.execute("""INSERT INTO assignments(id,classroom_id,title,instructions,due_at,created_by,status)
          VALUES(?,?,?,?,?,?,?)""", (aid,data.classroom_id,data.title.strip(),data.instructions,data.due_at,actor.id,data.status))
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
                AND (? IS NULL OR a.classroom_id=?) ORDER BY a.created_at DESC""",(classroom_id,classroom_id)).fetchall()
        else:
            rows=con.execute("""SELECT * FROM assignments WHERE (? IS NULL OR classroom_id=?)
                ORDER BY created_at DESC""",(classroom_id,classroom_id)).fetchall()
        return [dict(r) for r in rows]
    finally: con.close()

@router.get("/{assignment_id}")
def get_assignment(assignment_id: str, actor=Depends(current_actor)):
    con=connect()
    try: row=con.execute("SELECT * FROM assignments WHERE id=?",(assignment_id,)).fetchone()
    finally: con.close()
    if not row or (actor.role=="student" and row["status"]!="published"):
        raise HTTPException(404,"Asignación no encontrada")
    return dict(row)

@router.put("/{assignment_id}")
def update_assignment(assignment_id: str, data: AssignmentIn, expected_version: int = Query(ge=1), actor=Depends(current_actor)):
    require_roles(actor,"teacher","admin")
    if data.status not in {"draft","published","closed"}:
        raise HTTPException(422,"Estado inválido")
    with transaction() as con:
        existing=con.execute("SELECT created_by FROM assignments WHERE id=?",(assignment_id,)).fetchone()
        if not existing:
            raise HTTPException(404,"Asignación no encontrada")
        if actor.role=="teacher" and existing["created_by"] != actor.id:
            raise HTTPException(403,"Solo puedes modificar tus propias actividades")
        cur=con.execute("""UPDATE assignments SET title=?,instructions=?,classroom_id=?,due_at=?,status=?,
          version=version+1,updated_at=CURRENT_TIMESTAMP WHERE id=? AND version=?""",
          (data.title.strip(),data.instructions,data.classroom_id,data.due_at,data.status,assignment_id,expected_version))
        if cur.rowcount==0:
            exists=con.execute("SELECT 1 FROM assignments WHERE id=?",(assignment_id,)).fetchone()
            raise HTTPException(409 if exists else 404,"Conflicto de versión" if exists else "Asignación no encontrada")
        row=dict(con.execute("SELECT * FROM assignments WHERE id=?",(assignment_id,)).fetchone())
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id) VALUES(?,?,?,?)",
                    (actor.id,"update","assignment",assignment_id))
    log_event("assignment.updated", actor_id=actor.id, assignment_id=assignment_id, version=row["version"])
    return row
