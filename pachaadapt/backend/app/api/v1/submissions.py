from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
from app.db import connect, transaction
from app.core.security import current_actor, require_roles
from app.core.logging import log_event

router=APIRouter(prefix="/submissions",tags=["submissions"])
class SubmissionIn(BaseModel):
    assignment_id: str = Field(min_length=1)
    answer: str = Field(min_length=1, max_length=50000)
    client_updated_at: Optional[str] = None

@router.post("",status_code=201)
def submit(data: SubmissionIn, actor=Depends(current_actor)):
    if actor.role != "student":
        require_roles(actor,"student")
    sid=str(uuid4())
    with transaction() as con:
        a=con.execute("SELECT status FROM assignments WHERE id=?",(data.assignment_id,)).fetchone()
        if not a or a["status"]!="published": raise HTTPException(404,"Asignación no disponible")
        existing=con.execute("SELECT * FROM submissions WHERE assignment_id=? AND student_id=?",(data.assignment_id,actor.id)).fetchone()
        if existing:
            con.execute("""UPDATE submissions SET answer=?,client_updated_at=?,server_version=server_version+1,
              status='submitted',updated_at=CURRENT_TIMESTAMP WHERE id=?""",(data.answer.strip(),data.client_updated_at,existing["id"]))
            row=dict(con.execute("SELECT * FROM submissions WHERE id=?",(existing["id"],)).fetchone())
            action="update"
        else:
            con.execute("""INSERT INTO submissions(id,assignment_id,student_id,answer,client_updated_at)
              VALUES(?,?,?,?,?)""",(sid,data.assignment_id,actor.id,data.answer.strip(),data.client_updated_at))
            row=dict(con.execute("SELECT * FROM submissions WHERE id=?",(sid,)).fetchone())
            action="create"
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id) VALUES(?,?,?,?)",
                    (actor.id,action,"submission",row["id"]))
    log_event("submission.saved", actor_id=actor.id, submission_id=row["id"])
    return row

@router.get("")
def list_submissions(assignment_id: Optional[str]=None, actor=Depends(current_actor)):
    con=connect()
    try:
        if actor.role=="student":
            rows=con.execute("""SELECT * FROM submissions WHERE student_id=?
              AND (? IS NULL OR assignment_id=?) ORDER BY updated_at DESC""",(actor.id,assignment_id,assignment_id)).fetchall()
        elif actor.role=="teacher":
            rows=con.execute("""SELECT s.* FROM submissions s JOIN assignments a ON a.id=s.assignment_id
              WHERE a.created_by=? AND (? IS NULL OR s.assignment_id=?) ORDER BY s.updated_at DESC""",
              (actor.id,assignment_id,assignment_id)).fetchall()
        else:
            rows=con.execute("""SELECT * FROM submissions WHERE (? IS NULL OR assignment_id=?)
              ORDER BY updated_at DESC""",(assignment_id,assignment_id)).fetchall()
        return [dict(r) for r in rows]
    finally: con.close()

@router.patch("/{submission_id}/review")
def review(submission_id: str, status: str, actor=Depends(current_actor)):
    require_roles(actor,"teacher","admin")
    if status not in {"reviewed","returned"}: raise HTTPException(422,"Estado inválido")
    with transaction() as con:
        owner=con.execute("""SELECT a.created_by FROM submissions s JOIN assignments a
          ON a.id=s.assignment_id WHERE s.id=?""",(submission_id,)).fetchone()
        if not owner: raise HTTPException(404,"Entrega no encontrada")
        if actor.role=="teacher" and owner["created_by"] != actor.id:
            raise HTTPException(403,"No puedes revisar entregas de otra actividad")
        cur=con.execute("""UPDATE submissions SET status=?,server_version=server_version+1,
          updated_at=CURRENT_TIMESTAMP WHERE id=?""",(status,submission_id))
        if not cur.rowcount: raise HTTPException(404,"Entrega no encontrada")
        row=dict(con.execute("SELECT * FROM submissions WHERE id=?",(submission_id,)).fetchone())
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id,details_json) VALUES(?,?,?,?,?)",
                    (actor.id,"review","submission",submission_id,'{"status":"'+status+'"}'))
    log_event("submission.reviewed", actor_id=actor.id, submission_id=submission_id, status=status)
    return row
