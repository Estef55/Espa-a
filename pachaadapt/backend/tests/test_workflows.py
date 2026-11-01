import os, tempfile, uuid
from fastapi.testclient import TestClient

def setup_module():
    global dbfile
    fd,dbfile=tempfile.mkstemp(suffix=".db");os.close(fd)
    os.environ["PACHAADAPT_DB"]=dbfile
    os.environ["PACHAADAPT_I3_DEV_AUTH"]="1"
    from app.db import init_db
    init_db()

def headers(user="teacher-1",role="teacher"): return {"X-User-Id":user,"X-Role":role}

def test_assignment_submission_and_permissions():
    from app.main import app
    with TestClient(app) as c:
        a=c.post("/api/v1/assignments",headers=headers(),json={"title":"Actividad","instructions":"Resolver"})
        assert a.status_code==201
        aid=a.json()["id"]
        assert c.post("/api/v1/assignments",headers=headers("s1","student"),json={"title":"No"}).status_code==403
        s=c.post("/api/v1/submissions",headers=headers("s1","student"),json={"assignment_id":aid,"answer":"Mi respuesta"})
        assert s.status_code==201
        assert len(c.get("/api/v1/submissions",headers=headers("s1","student")).json())==1
        assert len(c.get("/api/v1/submissions",headers=headers("s2","student")).json())==0

def test_sync_is_idempotent_and_detects_conflict():
    from app.main import app
    with TestClient(app) as c:
        aid=c.post("/api/v1/assignments",headers=headers(),json={"title":"Offline"}).json()["id"]
        op={"operation_id":str(uuid.uuid4()),"entity_type":"submission","entity_id":aid,
            "payload":{"assignment_id":aid,"answer":"respuesta offline","base_version":0}}
        h=headers("s2","student")
        first=c.post("/api/v1/synchronization/push",headers=h,json=[op])
        second=c.post("/api/v1/synchronization/push",headers=h,json=[op])
        assert first.status_code==second.status_code==200
        assert first.json()==second.json()
        changed={**op,"payload":{**op["payload"],"answer":"otro contenido"}}
        assert c.post("/api/v1/synchronization/push",headers=h,json=[changed]).status_code==409

def test_assignment_optimistic_version_and_audit():
    from app.main import app
    from app.db import connect
    with TestClient(app) as c:
        a=c.post("/api/v1/assignments",headers=headers(),json={"title":"Versionada"}).json()
        updated=c.put(f"/api/v1/assignments/{a['id']}?expected_version=1",headers=headers(),
                      json={"title":"Actualizada","instructions":"","status":"published"})
        assert updated.status_code==200 and updated.json()["version"]==2
        conflict=c.put(f"/api/v1/assignments/{a['id']}?expected_version=1",headers=headers(),
                       json={"title":"Antigua","instructions":"","status":"published"})
        assert conflict.status_code==409
        con=connect()
        try:
            assert con.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]>=2
            versions=[x[0] for x in con.execute("SELECT version FROM schema_migrations ORDER BY version")]
            assert versions==[1,2,3]
        finally: con.close()

def test_sync_rejects_non_student_and_bad_uuid():
    from app.main import app
    with TestClient(app) as c:
        aid=c.post("/api/v1/assignments",headers=headers(),json={"title":"Permisos"}).json()["id"]
        op={"operation_id":"not-a-uuid","entity_type":"submission","entity_id":aid,
            "payload":{"assignment_id":aid,"answer":"x","base_version":0}}
        assert c.post("/api/v1/synchronization/push",headers=headers("teacher-1","teacher"),json=[op]).status_code==422


def test_student_cannot_see_drafts_or_review_submissions():
    from app.main import app
    with TestClient(app) as c:
        draft=c.post("/api/v1/assignments",headers=headers(),json={"title":"Borrador","status":"draft"}).json()
        assert c.get(f"/api/v1/assignments/{draft['id']}",headers=headers("s3","student")).status_code==404
        assert c.get("/api/v1/assignments",headers=headers("s3","student")).status_code==200
        published=c.post("/api/v1/assignments",headers=headers(),json={"title":"Publicada"}).json()
        sub=c.post("/api/v1/submissions",headers=headers("s3","student"),
                    json={"assignment_id":published["id"],"answer":"Respuesta"}).json()
        assert c.patch(f"/api/v1/submissions/{sub['id']}/review?status=reviewed",
                       headers=headers("s3","student")).status_code==403


def test_teacher_can_only_manage_own_assignments_and_submissions():
    from app.main import app
    with TestClient(app) as c:
        owned=c.post("/api/v1/assignments",headers=headers("t1","teacher"),
                     json={"title":"Actividad de T1"}).json()
        other=c.post("/api/v1/assignments",headers=headers("t2","teacher"),
                     json={"title":"Actividad de T2"}).json()
        assert c.put(f"/api/v1/assignments/{owned['id']}?expected_version=1",headers=headers("t2","teacher"),
                     json={"title":"Cambio ajeno","instructions":"","status":"published"}).status_code==403
        sub=c.post("/api/v1/submissions",headers=headers("s4","student"),
                   json={"assignment_id":owned["id"],"answer":"Respuesta"}).json()
        assert c.patch(f"/api/v1/submissions/{sub['id']}/review?status=reviewed",
                       headers=headers("t2","teacher")).status_code==403
        assert c.get("/api/v1/submissions",headers=headers("t2","teacher")).json()==[]


def test_materials_are_cached_metadata_and_roles_are_enforced():
    from app.main import app
    with TestClient(app) as c:
        created=c.post("/api/v1/material-library",headers=headers("teacher-material","teacher"),
                       json={"title":"Lectura","description":"PDF de lectura",
                             "resource_url":"/resources/lectura.pdf","mime_type":"application/pdf"})
        assert created.status_code==201
        invalid=c.post("/api/v1/material-library",headers=headers("teacher-material","teacher"),
                       json={"title":"Malicioso","resource_url":"javascript:alert(1)"})
        assert invalid.status_code==422
        assert len(c.get("/api/v1/material-library",headers=headers("student-material","student")).json())==1
        draft=c.post("/api/v1/material-library",headers=headers("teacher-material","teacher"),
                     json={"title":"Borrador","resource_url":"/resources/borrador.pdf","status":"draft"})
        assert draft.status_code==201
        student_items=c.get("/api/v1/material-library",headers=headers("student-material","student")).json()
        assert all(x["status"]=="published" for x in student_items)
        assert c.get(f"/api/v1/material-library/{created.json()['id']}",
                     headers=headers("other-teacher","teacher")).status_code==403


def test_sync_pull_and_status_endpoints():
    from app.main import app
    with TestClient(app) as c:
        aid=c.post("/api/v1/assignments",headers=headers(),json={"title":"Pull visible"}).json()["id"]
        student=headers("pull-student","student")
        pulled=c.get("/api/v1/synchronization/pull",headers=student)
        assert pulled.status_code==200
        assert any(x["id"]==aid for x in pulled.json()["assignments"])
        status=c.get("/api/v1/synchronization/status",headers=student)
        assert status.status_code==200 and status.json()["server"]=="online"


def test_sync_batch_limit_is_enforced():
    from app.main import app
    with TestClient(app) as c:
        response=c.post("/api/v1/synchronization/push",headers=headers("batch-student","student"),json=[{}]*101)
        assert response.status_code==413


def test_database_migrations_are_idempotent_and_health_is_ok():
    from app.db import init_db
    from app.main import app
    from app.db import connect
    init_db()
    init_db()
    con=connect()
    try:
        versions=[row[0] for row in con.execute("SELECT version FROM schema_migrations ORDER BY version")]
        assert versions==[1,2,3]
    finally:
        con.close()
    with TestClient(app) as c:
        response=c.get("/health")
        assert response.status_code==200
        assert response.json()["database"]=="ok"
