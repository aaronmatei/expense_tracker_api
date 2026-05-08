
from fastapi import FastAPI

from app.config import settings
from app.routers import auth, categories, users


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug
)

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(categories.router)


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
