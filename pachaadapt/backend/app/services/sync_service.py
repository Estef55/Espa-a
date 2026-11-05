"""Aplicación idempotente de cambios offline con detección de conflictos."""
from contextlib import nullcontext
import hashlib
import json
from uuid import UUID, uuid4
from fastapi import HTTPException
from app.db import transaction
from app.core.logging import log_event


def apply_operation(op, actor, con=None):
    required={"operation_id","entity_type","entity_id","payload"}
    if not isinstance(op, dict) or not required.issubset(op):
        raise HTTPException(422,"Operación incompleta")
    try:
        oid=str(UUID(str(op["operation_id"])))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422,"operation_id debe ser un UUID válido")
    entity=str(op["entity_type"])
    eid=str(op["entity_id"])
    payload=op["payload"]
    if not isinstance(payload, dict):
        raise HTTPException(422,"payload debe ser un objeto JSON")
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    with (transaction() if con is None else nullcontext(con)) as con:
        prior=con.execute("SELECT actor_id,payload_hash,result_json FROM sync_operations WHERE operation_id=?",(oid,)).fetchone()
        if prior:
            if prior["actor_id"] != actor.id:
                raise HTTPException(409,"operation_id ya pertenece a otro usuario")
            if prior["payload_hash"] != digest:
                raise HTTPException(409,"operation_id reutilizado con contenido distinto")
            return json.loads(prior["result_json"])
        if entity != "submission":
            raise HTTPException(422,"Tipo de entidad no sincronizable")
        if actor.role != "student":
            raise HTTPException(403,"Solo estudiantes pueden sincronizar entregas")
        aid=payload.get("assignment_id")
        answer=payload.get("answer")
        if not aid or str(aid) != eid or not isinstance(answer,str) or not answer.strip() or len(answer)>50000:
            raise HTTPException(422,"Entrega inválida")
        assignment=con.execute("SELECT status,classroom_id,is_demo FROM assignments WHERE id=?",(aid,)).fetchone()
        if not assignment or assignment["status"]!="published":
            result={"operation_id":oid,"status":"rejected","reason":"assignment_unavailable"}
        elif assignment["classroom_id"] and not con.execute(
            "SELECT 1 FROM classroom_members WHERE classroom_id=? AND user_id=? AND member_role='student'",
            (assignment["classroom_id"], actor.id)).fetchone():
            result={"operation_id":oid,"status":"rejected","reason":"student_not_enrolled"}
        else:
            current=con.execute("SELECT * FROM submissions WHERE assignment_id=? AND student_id=?",(aid,actor.id)).fetchone()
            base=payload.get("base_version",0)
            if not isinstance(base,int) or base < 0:
                raise HTTPException(422,"base_version inválida")
            if current and current["status"] in {"reviewed", "returned"}:
                result={"operation_id":oid,"status":"conflict","server":dict(current),"local":payload,
                        "reason":"submission_already_reviewed"}
            elif current and base != int(current["server_version"]):
                result={"operation_id":oid,"status":"conflict","server":dict(current),"local":payload}
            elif current:
                con.execute("""UPDATE submissions SET answer=?,client_updated_at=?,score=NULL,max_score=NULL,
                    validation_status='pending',reviewed_at=NULL,is_demo=?,server_version=server_version+1,
                    status='submitted',updated_at=CURRENT_TIMESTAMP WHERE id=?""",
                    (answer.strip(),payload.get("client_updated_at"),int(assignment["is_demo"]),current["id"]))
                result={"operation_id":oid,"status":"acknowledged",
                        "entity":dict(con.execute("SELECT * FROM submissions WHERE id=?",(current["id"],)).fetchone())}
            else:
                sid=str(uuid4())
                con.execute("""INSERT INTO submissions(id,assignment_id,student_id,answer,client_updated_at,is_demo)
                    VALUES(?,?,?,?,?,?)""",(sid,aid,actor.id,answer.strip(),payload.get("client_updated_at"),int(assignment["is_demo"])))
                result={"operation_id":oid,"status":"acknowledged",
                        "entity":dict(con.execute("SELECT * FROM submissions WHERE id=?",(sid,)).fetchone())}
        con.execute("""INSERT INTO sync_operations(operation_id,actor_id,entity_type,entity_id,payload_hash,result_json)
            VALUES(?,?,?,?,?,?)""",(oid,actor.id,entity,eid,digest,json.dumps(result,ensure_ascii=False)))
        con.execute("INSERT INTO audit_log(actor_id,action,entity_type,entity_id,details_json) VALUES(?,?,?,?,?)",
                    (actor.id,"sync_"+result["status"],entity,eid,json.dumps({"operation_id":oid})))
    log_event("sync.operation", actor_id=actor.id, operation_id=oid, status=result["status"])
    return result
