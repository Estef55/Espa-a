from fastapi import APIRouter, Depends, Query
from typing import List, Dict, Any
from app.db import connect
from app.core.security import current_actor
from app.services.sync_service import apply_operation

router=APIRouter(prefix="/synchronization",tags=["synchronization"])

@router.post("/push")
def push(operations: List[Dict[str,Any]], actor=Depends(current_actor)):
    if len(operations)>100:
        from fastapi import HTTPException
        raise HTTPException(413,"Máximo 100 operaciones por lote")
    results=[apply_operation(op,actor) for op in operations]
    return {"results":results,"received":len(results),"acknowledged":sum(x["status"]=="acknowledged" for x in results),
            "conflicts":sum(x["status"]=="conflict" for x in results),
            "rejected":sum(x["status"]=="rejected" for x in results)}

@router.get("/pull")
def pull(since: str = Query(default="1970-01-01 00:00:00"), actor=Depends(current_actor)):
    con=connect()
    try:
        if actor.role=="student":
            assignments=con.execute("""SELECT * FROM assignments WHERE status='published' AND updated_at>?
                ORDER BY updated_at""",(since,)).fetchall()
            submissions=con.execute("""SELECT * FROM submissions WHERE student_id=? AND updated_at>?
                ORDER BY updated_at""",(actor.id,since)).fetchall()
        else:
            assignments=con.execute("SELECT * FROM assignments WHERE updated_at>? ORDER BY updated_at",(since,)).fetchall()
            submissions=con.execute("SELECT * FROM submissions WHERE updated_at>? ORDER BY updated_at",(since,)).fetchall()
        return {"assignments":[dict(x) for x in assignments],"submissions":[dict(x) for x in submissions],
                "server_time":con.execute("SELECT CURRENT_TIMESTAMP").fetchone()[0]}
    finally: con.close()

@router.get("/status")
def status(actor=Depends(current_actor)):
    con=connect()
    try:
        accepted=con.execute("SELECT COUNT(*) FROM sync_operations WHERE actor_id=? AND received_at >= datetime('now','-1 day')",(actor.id,)).fetchone()[0]
        last=con.execute("SELECT MAX(received_at) FROM sync_operations WHERE actor_id=?",(actor.id,)).fetchone()[0]
        return {"server":"online","accepted_last_24h":accepted,"last_received_at":last,"actor_id":actor.id}
    finally: con.close()
