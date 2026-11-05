"""Carga determinista y aislada de datos ficticios para PACHAADAPT.

Uso:
  python database/seed_data.py             # crea/actualiza demo, sin duplicar
  python database/seed_data.py --reset     # elimina SOLO filas marcadas is_demo=1
  python database/seed_data.py --reset --seed  # reinicia y vuelve a cargar
Nunca modifica filas reales (is_demo=0).
"""
import argparse
import sys
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db import init_db, transaction, connect

def uid(key: str) -> str:
    return str(uuid5(NAMESPACE_URL, "pachaadapt:demo:" + key))

TEACHER = "demo-teacher"
CLASSROOM = uid("classroom")
STUDENTS = ["demo-student", uid("student-2"), uid("student-3")]
MATERIAL = uid("material")
ASSIGNMENTS = [uid("assignment-1"), uid("assignment-2")]

def reset_demo():
    with transaction() as con:
        con.execute("DELETE FROM submissions WHERE is_demo=1")
        con.execute("DELETE FROM assignments WHERE is_demo=1")
        con.execute("DELETE FROM materials WHERE is_demo=1")
        con.execute("DELETE FROM classroom_members WHERE classroom_id IN (SELECT id FROM classrooms WHERE is_demo=1)")
        con.execute("DELETE FROM classrooms WHERE is_demo=1")
        con.execute("DELETE FROM users WHERE is_demo=1")

def seed():
    init_db()
    with transaction() as con:
        # Refuse collisions with real records instead of converting them into demo data.
        demo_user_ids = [TEACHER, *STUDENTS]
        for user_id in demo_user_ids:
            existing = con.execute("SELECT is_demo FROM users WHERE id=?", (user_id,)).fetchone()
            if existing and not existing["is_demo"]:
                raise RuntimeError(f"Colisión con usuario real {user_id}; se cancela la carga demo")
        con.execute("INSERT INTO users(id,display_name,role,is_demo) VALUES(?,?,?,1) "
                    "ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name, role=excluded.role, is_demo=1",
                    (TEACHER, "Docente ficticio de demostración", "teacher"))
        for i, sid in enumerate(STUDENTS, 1):
            con.execute("INSERT INTO users(id,display_name,role,is_demo) VALUES(?,?,?,1) "
                        "ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name, role=excluded.role, is_demo=1",
                        (sid, f"Estudiante ficticio {i}", "student"))
        con.execute("INSERT INTO classrooms(id,name,teacher_id,is_demo) VALUES(?,?,?,1) "
                    "ON CONFLICT(id) DO UPDATE SET name=excluded.name, teacher_id=excluded.teacher_id, is_demo=1",
                    (CLASSROOM, "Aula PACHAADAPT de demostración", TEACHER))
        con.execute("INSERT OR IGNORE INTO classroom_members(classroom_id,user_id,member_role) VALUES(?,?,?)",
                    (CLASSROOM, TEACHER, "teacher"))
        for sid in STUDENTS:
            con.execute("INSERT OR IGNORE INTO classroom_members(classroom_id,user_id,member_role) VALUES(?,?,?)",
                        (CLASSROOM, sid, "student"))
        con.execute("""INSERT INTO materials(id,title,description,resource_url,mime_type,created_by,status,is_demo)
            VALUES(?,?,?,?,?,?,?,1) ON CONFLICT(id) DO UPDATE SET title=excluded.title,
            description=excluded.description, resource_url=excluded.resource_url,
            mime_type=excluded.mime_type, created_by=excluded.created_by,status=excluded.status,is_demo=1""",
            (MATERIAL, "Material ficticio: biodiversidad local",
             "Texto educativo de ejemplo para la demostración.", "/demo/biodiversidad.txt",
             "text/plain", TEACHER, "published"))
        titles = ["Identificación de especies", "Conservación de ecosistemas"]
        for i, aid in enumerate(ASSIGNMENTS):
            con.execute("""INSERT INTO assignments(id,classroom_id,title,instructions,created_by,status,material_id,is_demo)
                VALUES(?,?,?,?,?,'published',?,1) ON CONFLICT(id) DO UPDATE SET
                classroom_id=excluded.classroom_id,title=excluded.title,instructions=excluded.instructions,
                created_by=excluded.created_by,status='published',material_id=excluded.material_id,is_demo=1""",
                (aid, CLASSROOM, titles[i], "Actividad ficticia de demostración. Responde con tus propias palabras.",
                 TEACHER, MATERIAL))
        # Seis resultados sintéticos, claramente etiquetados como demo, tres estudiantes.
        scores = [(0,0,8),(0,1,7),(0,2,9),(1,0,6),(1,1,8),(1,2,7)]
        for ai, si, score in scores:
            sid = uid(f"submission-{ai}-{si}")
            con.execute("""INSERT INTO submissions(id,assignment_id,student_id,answer,status,score,max_score,
                validation_status,reviewed_at,is_demo)
                VALUES(?,?,?,?,'reviewed',?,10,'validated',CURRENT_TIMESTAMP,1)
                ON CONFLICT(assignment_id,student_id) DO UPDATE SET
                answer=excluded.answer,status='reviewed',score=excluded.score,max_score=10,
                validation_status='validated',reviewed_at=CURRENT_TIMESTAMP,is_demo=1""",
                (sid, ASSIGNMENTS[ai], STUDENTS[si],
                 "Respuesta ficticia de demostración; no representa a una persona real.", score))
    print("Datos ficticios de PACHAADAPT cargados de forma idempotente.")
    print(f"Aula: {CLASSROOM}; docente: {TEACHER}; estudiantes: {len(STUDENTS)}; actividades: {len(ASSIGNMENTS)}; resultados demo: 6.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="elimina únicamente registros is_demo=1")
    parser.add_argument("--seed", action="store_true", help="vuelve a cargar tras --reset")
    args = parser.parse_args()
    init_db()
    if args.reset:
        reset_demo()
    if not args.reset or args.seed:
        seed()
    else:
        print("Datos de demostración eliminados; los registros reales se conservaron.")
