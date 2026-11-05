from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from uuid import uuid4
import math
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
    if not data.answer.strip():
        raise HTTPException(422, "La respuesta no puede estar vacía")
    sid=str(uuid4())
    with transaction() as con:
        a=con.execute("SELECT status,classroom_id,is_demo FROM assignments WHERE id=?",(data.assignment_id,)).fetchone()
        if not a or a["status"]!="published": raise HTTPException(404,"Asignación no disponible")
        if a["classroom_id"] and not con.execute(
            "SELECT 1 FROM classroom_members WHERE classroom_id=? AND user_id=? AND member_role='student'",
            (a["classroom_id"], actor.id)).fetchone():
            raise HTTPException(403, "No perteneces al aula de esta actividad")
        existing=con.execute("SELECT * FROM submissions WHERE assignment_id=? AND student_id=?",(data.assignment_id,actor.id)).fetchone()
        if existing:
            if existing["status"] in {"reviewed", "returned"} or existing["validation_status"] == "validated":
                raise HTTPException(409, "La entrega ya fue revisada; solicita al docente que habilite una nueva entrega")
            con.execute("""UPDATE submissions SET answer=?,client_updated_at=?,score=NULL,max_score=NULL,
              validation_status='pending',reviewed_at=NULL,is_demo=?,server_version=server_version+1,
              status='submitted',updated_at=CURRENT_TIMESTAMP WHERE id=?""",
              (data.answer.strip(),data.client_updated_at,int(a["is_demo"]),existing["id"]))
            row=dict(con.execute("SELECT * FROM submissions WHERE id=?",(existing["id"],)).fetchone())
            action="update"
        else:
            con.execute("""INSERT INTO submissions(id,assignment_id,student_id,answer,client_updated_at,is_demo)
              VALUES(?,?,?,?,?,?)""",(sid,data.assignment_id,actor.id,data.answer.strip(),data.client_updated_at,int(a["is_demo"])))
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
def review(submission_id: str, status: str, score: Optional[float] = None,
           max_score: Optional[float] = None, validation_status: str = "pending",
           actor=Depends(current_actor)):
    require_roles(actor,"teacher","admin")
    if status not in {"reviewed","returned"}: raise HTTPException(422,"Estado inválido")
    if validation_status not in {"pending", "validated", "rejected"}:
        raise HTTPException(422, "validation_status inválido")
    if score is not None or max_score is not None:
        if (score is None or max_score is None or not math.isfinite(score) or not math.isfinite(max_score)
                or max_score <= 0 or score < 0 or score > max_score):
            raise HTTPException(422, "score y max_score deben ser válidos y score no puede superar max_score")
    if validation_status == "validated" and (status != "reviewed" or score is None or max_score is None):
        raise HTTPException(422, "Para validar un resultado se requiere revisión y puntuación explícita")
    if validation_status == "rejected" and status != "returned":
        raise HTTPException(422, "Una entrega rechazada debe quedar en estado returned")
    with transaction() as con:
        owner=con.execute("""SELECT a.created_by,s.status,s.validation_status FROM submissions s JOIN assignments a
          ON a.id=s.assignment_id WHERE s.id=?""",(submission_id,)).fetchone()
        if not owner: raise HTTPException(404,"Entrega no encontrada")
        if actor.role=="teacher" and owner["created_by"] != actor.id:
            raise HTTPException(403,"No puedes revisar entregas de otra actividad")
        if owner["validation_status"] == "validated":
            raise HTTPException(409, "El resultado ya está validado; no puede sobrescribirse")
        cur=con.execute("""UPDATE submissions SET status=?, score=?, max_score=?, validation_status=?,
          reviewed_at=CURRENT_TIMESTAMP, server_version=server_version+1, updated_at=CURRENT_TIMESTAMP
          WHERE id=?""",(status,score,max_score,validation_status,submission_id))
        if not cur.rowcount: raise HTTPException(404,"Entrega no encontrada")
        row=dict(con.execute("SELECT * FROM submissions WHERE id=?",(submission_id,)).fetchone())
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id,details_json) VALUES(?,?,?,?,?)",
                    (actor.id,"review","submission",submission_id,
                     __import__("json").dumps({"status":status,"score":score,"max_score":max_score,
                                               "validation_status":validation_status})))
    log_event("submission.reviewed", actor_id=actor.id, submission_id=submission_id, status=status)
    return row
