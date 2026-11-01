"""Inserta una actividad demostrativa sin duplicarla."""
import sys
from pathlib import Path
from uuid import uuid5, NAMESPACE_URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db import init_db, transaction

def seed():
    init_db()
    teacher_id = "demo-teacher"
    student_id = "demo-student"
    assignment_id = str(uuid5(NAMESPACE_URL, "pachaadapt:actividad-demostracion"))
    with transaction() as con:
        con.execute("INSERT OR IGNORE INTO users(id,display_name,role) VALUES(?,?,?)",
                    (teacher_id,"Docente de demostración","teacher"))
        con.execute("INSERT OR IGNORE INTO users(id,display_name,role) VALUES(?,?,?)",
                    (student_id,"Estudiante de demostración","student"))
        con.execute("""INSERT OR IGNORE INTO assignments
            (id,title,instructions,created_by,status)
            VALUES(?,?,?,?,?)""",
            (assignment_id,"Actividad de demostración",
             "Explica con tus propias palabras qué aprendiste hoy.",teacher_id,"published"))
    print(f"Datos de demostración listos. Actividad: {assignment_id}")

if __name__ == "__main__":
    seed()
