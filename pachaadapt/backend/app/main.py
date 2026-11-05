"""Aplicación PACHAADAPT con módulos de integración aditivos."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.register import register_integrante3
from app.api.v1.materials import router as materials_router
from app.api.v1.adaptations import router as adaptations_router  # integrante 2
from app.api.v1.assignments import router as assignments_router
from app.api.v1.classrooms import router as classrooms_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.synchronization import router as synchronization_router
from app.api.v1.library_materials import router as library_materials_router
from app.core.config import settings
from app.services.container import configure_integrations
from app.services.learning_data_source import SQLiteLearningDataSource
from app.services.material_integration import MaterialDocumentProcessor
from app.db import healthcheck, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Adaptador aditivo: reutiliza los materiales del integrante 2 y verifica propietario.
    configure_integrations(
        processor=MaterialDocumentProcessor(),
        data_source=SQLiteLearningDataSource(),
    )
    yield


app = FastAPI(
    title=settings.app_name,
    description="PACHAADAPT: materiales educativos, actividades, entregas y sincronización offline.",
    version="1.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-User-Id", "X-Role", "X-Dev-Teacher-Id", "X-Dev-Role"],
)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "project": "PACHAADAPT by YACHAY", **healthcheck()}


register_integrante3(app)
app.include_router(materials_router, prefix="/api/v1")
app.include_router(adaptations_router, prefix="/api/v1")  # integrante 2
app.include_router(assignments_router, prefix="/api/v1")
app.include_router(classrooms_router, prefix="/api/v1")
app.include_router(submissions_router, prefix="/api/v1")
app.include_router(synchronization_router, prefix="/api/v1")
app.include_router(library_materials_router, prefix="/api/v1")

