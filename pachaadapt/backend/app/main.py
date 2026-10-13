from fastapi import FastAPI

app = FastAPI(title="PACHAADAPT by YACHAY", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "project": "PACHAADAPT by YACHAY"}
