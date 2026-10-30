from fastapi import FastAPI
from app.api.v1.materials import router as materials_router

app = FastAPI(title="PACHAADAPT by YACHAY", version="0.2.0")
app.include_router(materials_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok", "project": "PACHAADAPT by YACHAY"}
