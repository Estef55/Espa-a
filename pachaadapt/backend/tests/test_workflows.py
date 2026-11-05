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
            assert versions==[1,2,3,4]
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
        # Teachers must not enumerate or pull another teacher's records.
        assert all(x["id"] != owned["id"] for x in c.get("/api/v1/assignments",headers=headers("t2","teacher")).json())
        pulled=c.get("/api/v1/synchronization/pull",headers=headers("t2","teacher")).json()
        assert all(x["id"] != owned["id"] for x in pulled["assignments"])
        assert all(x["assignment_id"] != owned["id"] for x in pulled["submissions"])


def test_sync_cannot_silently_overwrite_teacher_review():
    from app.main import app
    with TestClient(app) as c:
        aid=c.post("/api/v1/assignments",headers=headers(),json={"title":"Respuesta revisada"}).json()["id"]
        student=headers("review-student","student")
        submission=c.post("/api/v1/submissions",headers=student,
                          json={"assignment_id":aid,"answer":"original"}).json()
        reviewed=c.patch(f"/api/v1/submissions/{submission['id']}/review?status=reviewed",
                         headers=headers(),json=None).json()
        operation={"operation_id":str(uuid.uuid4()),"entity_type":"submission","entity_id":aid,
                   "payload":{"assignment_id":aid,"answer":"respuesta reenviada",
                              "base_version":reviewed["server_version"]}}
        response=c.post("/api/v1/synchronization/push",headers=student,json=[operation])
        assert response.status_code==200
        assert response.json()["results"][0]["status"]=="conflict"
        current=c.get("/api/v1/submissions",headers=student).json()[0]
        assert current["answer"]=="original" and current["status"]=="reviewed"



def test_sync_push_batch_rolls_back_when_later_operation_is_invalid():
    from app.main import app
    from app.db import connect
    with TestClient(app) as c:
        aid=c.post("/api/v1/assignments",headers=headers(),json={"title":"Batch atomic"}).json()["id"]
        first={"operation_id":str(uuid.uuid4()),"entity_type":"submission","entity_id":aid,
               "payload":{"assignment_id":aid,"answer":"first","base_version":0}}
        invalid={"operation_id":"invalid","entity_type":"submission","entity_id":aid,
                 "payload":{"assignment_id":aid,"answer":"second","base_version":0}}
        response=c.post("/api/v1/synchronization/push",headers=headers("batch-atomic","student"),json=[first,invalid])
        assert response.status_code==422
        con=connect()
        try:
            assert con.execute("SELECT COUNT(*) FROM submissions WHERE student_id=?",("batch-atomic",)).fetchone()[0]==0
            assert con.execute("SELECT COUNT(*) FROM sync_operations WHERE operation_id=?",(first["operation_id"],)).fetchone()[0]==0
        finally: con.close()



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
        assert versions==[1,2,3,4]
    finally:
        con.close()
    with TestClient(app) as c:
        response=c.get("/health")
        assert response.status_code==200
        assert response.json()["database"]=="ok"


def test_classroom_membership_and_only_validated_scores_feed_reports():
    from app.main import app
    from app.services.learning_data_source import SQLiteLearningDataSource
    from app.db import connect
    with TestClient(app) as c:
        teacher = headers("report-teacher", "teacher")
        classroom = c.post("/api/v1/classrooms", headers=teacher, json={"name":"Aula autorizada"})
        assert classroom.status_code == 201
        cid = classroom.json()["id"]
        students = ["report-s1", "report-s2", "report-s3"]
        from app.db import transaction
        with transaction() as con:
            for sid in students:
                con.execute("INSERT INTO users(id,display_name,role) VALUES(?,?, 'student')",
                            (sid, sid))
        for sid in students:
            assert c.post(f"/api/v1/classrooms/{cid}/members", headers=teacher,
                          json={"user_id":sid}).status_code == 201
        a = c.post("/api/v1/assignments", headers=teacher,
                   json={"title":"Biodiversidad","classroom_id":cid}).json()
        assert c.post("/api/v1/submissions", headers=headers("outsider","student"),
                      json={"assignment_id":a["id"],"answer":"No autorizado"}).status_code == 403
        submissions = []
        for sid in students:
            response = c.post("/api/v1/submissions", headers=headers(sid,"student"),
                              json={"assignment_id":a["id"],"answer":"Respuesta de prueba"})
            assert response.status_code == 201
            submissions.append(response.json())
        # Explicit score and validation required. Pending reviewed records do not enter reports.
        reviewed = c.patch(f"/api/v1/submissions/{submissions[0]['id']}/review?status=reviewed&score=8&max_score=10&validation_status=validated",
                           headers=teacher)
        assert reviewed.status_code == 200
        pending = c.patch(f"/api/v1/submissions/{submissions[1]['id']}/review?status=reviewed",
                          headers=teacher)
        assert pending.status_code == 200
        source = SQLiteLearningDataSource()
        rows = source.fetch_records("report-teacher", {})
        assert len(rows) == 1
        assert rows[0].score == 8 and rows[0].max_score == 10
        assert rows[0].student_ref != students[0]
        # A different teacher cannot obtain these classroom records.
        assert source.fetch_records("another-teacher", {}) == []


def test_demo_seed_is_idempotent_and_reset_preserves_real_records(tmp_path):
    import os, subprocess, sys
    dbfile = str(tmp_path / "demo.sqlite3")
    env = os.environ.copy()
    env["PACHAADAPT_DB_PATH"] = dbfile
    script = str(__import__("pathlib").Path(__file__).resolve().parents[2] / "database" / "seed_data.py")
    subprocess.run([sys.executable, script], env=env, check=True, capture_output=True, text=True)
    subprocess.run([sys.executable, script], env=env, check=True, capture_output=True, text=True)
    from app.db import connect, transaction
    # Current process DB path follows the test module's own database; use sqlite directly for this isolated file.
    import sqlite3
    con = sqlite3.connect(dbfile)
    assert con.execute("SELECT COUNT(*) FROM classrooms WHERE is_demo=1").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM submissions WHERE is_demo=1").fetchone()[0] == 6
    con.execute("INSERT INTO users(id,display_name,role) VALUES('real-user','Usuario real','student')")
    con.commit(); con.close()
    subprocess.run([sys.executable, script, "--reset"], env=env, check=True, capture_output=True, text=True)
    con = sqlite3.connect(dbfile)
    assert con.execute("SELECT COUNT(*) FROM classrooms WHERE is_demo=1").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM users WHERE id='real-user'").fetchone()[0] == 1
    con.close()


def test_direct_submission_cannot_overwrite_reviewed_or_validated_result():
    from app.main import app
    with TestClient(app) as c:
        teacher = headers("lock-teacher", "teacher")
        a = c.post("/api/v1/assignments", headers=teacher, json={"title":"Entrega protegida"}).json()
        student = headers("lock-student", "student")
        sub = c.post("/api/v1/submissions", headers=student,
                     json={"assignment_id":a["id"],"answer":"Respuesta inicial"}).json()
        reviewed = c.patch(
            f"/api/v1/submissions/{sub['id']}/review?status=reviewed&score=9&max_score=10&validation_status=validated",
            headers=teacher)
        assert reviewed.status_code == 200
        overwritten = c.post("/api/v1/submissions", headers=student,
                             json={"assignment_id":a["id"],"answer":"Intento de sobrescritura"})
        assert overwritten.status_code == 409
        current = c.get("/api/v1/submissions", headers=student).json()[0]
        assert current["answer"] == "Respuesta inicial"
        assert current["score"] == 9 and current["validation_status"] == "validated"


def test_demo_and_real_records_are_separated_in_report_source(tmp_path):
    import os, subprocess, sys, sqlite3
    from pathlib import Path
    dbfile = str(tmp_path / "isolated.sqlite3")
    env = os.environ.copy()
    env["PACHAADAPT_DB_PATH"] = dbfile
    script = str(Path(__file__).resolve().parents[2] / "database" / "seed_data.py")
    subprocess.run([sys.executable, script], env=env, check=True, capture_output=True)
    # A real classroom owned by a non-demo teacher is never mixed into demo scope.
    con = sqlite3.connect(dbfile)
    assert con.execute("SELECT COUNT(*) FROM classrooms WHERE is_demo=1").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM submissions WHERE is_demo=1").fetchone()[0] == 6
    con.close()
    from ai.settings import load_settings
    assert load_settings({}).dev_auth is False
    previous = os.environ.get("PACHAADAPT_DB_PATH")
    os.environ["PACHAADAPT_DB_PATH"] = dbfile
    try:
        from app.services.learning_data_source import SQLiteLearningDataSource
        source = SQLiteLearningDataSource()
        from database.seed_data import TEACHER
        assert len(source.fetch_records(TEACHER, {})) == 6
        assert source.fetch_records("ordinary-teacher", {}) == []
    finally:
        if previous is None:
            os.environ.pop("PACHAADAPT_DB_PATH", None)
        else:
            os.environ["PACHAADAPT_DB_PATH"] = previous


def test_demo_seed_refuses_collision_with_real_demo_namespace(tmp_path):
    import os, subprocess, sys, sqlite3
    from pathlib import Path
    dbfile = str(tmp_path / "collision.sqlite3")
    env = os.environ.copy()
    env["PACHAADAPT_DB_PATH"] = dbfile
    script = str(Path(__file__).resolve().parents[2] / "database" / "seed_data.py")
    # Prepare an existing real account using the reserved demo ID.
    subprocess.run([sys.executable, "-c", (
        "import os,sys; sys.path.insert(0, 'backend'); "
        "from app.db import init_db,transaction; init_db(); "
        "c=transaction(); con=c.__enter__(); "
        "con.execute(\"INSERT INTO users(id,display_name,role) VALUES('demo-teacher','Real','student')\"); "
        "c.__exit__(None,None,None)"
    )], cwd=Path(__file__).resolve().parents[2], env=env, check=True, capture_output=True)
    result = subprocess.run([sys.executable, script], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    con = sqlite3.connect(dbfile)
    try:
        assert con.execute("SELECT display_name,role,is_demo FROM users WHERE id='demo-teacher'").fetchone() == ("Real", "student", 0)
        assert con.execute("SELECT COUNT(*) FROM classrooms WHERE is_demo=1").fetchone()[0] == 0
    finally:
        con.close()


def test_validated_results_without_classroom_are_scoped_to_assignment_owner():
    from app.main import app
    from app.services.learning_data_source import SQLiteLearningDataSource
    with TestClient(app) as client:
        teacher = headers("solo-report-teacher", "teacher")
        assignment = client.post("/api/v1/assignments", headers=teacher,
                                 json={"title":"Actividad individual"}).json()
        student = headers("solo-report-student", "student")
        submission = client.post("/api/v1/submissions", headers=student,
                                 json={"assignment_id":assignment["id"],"answer":"Respuesta"}).json()
        reviewed = client.patch(
            f"/api/v1/submissions/{submission['id']}/review?status=reviewed&score=8&max_score=10&validation_status=validated",
            headers=teacher)
        assert reviewed.status_code == 200
        rows = SQLiteLearningDataSource().fetch_records("solo-report-teacher", {})
        assert len(rows) == 1
        assert rows[0].score == 8
        assert SQLiteLearningDataSource().fetch_records("different-teacher", {}) == []
