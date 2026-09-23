from fastapi import FastAPI
from backend.database import init_db

app = FastAPI(title="CAT Smart Operator Assistant")

init_db()

@app.get("/health")
def health():
    return {"status": "ok"}