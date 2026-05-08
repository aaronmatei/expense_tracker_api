from fastapi import FastAPI
from app.config import settings

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug)


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": f"{settings.app_name} is running!",
        "environment": settings.environment
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "message": "API is healthy!"
    }
