from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.config import settings

from app.database import Base, engine
from app.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup. In production, you would typically use
    # Alembic for migrations instead of creating tables directly from models.
    print(">>> Lifespan starting, creating tables...")
    Base.metadata.create_all(bind=engine)
    print(">>> Tables created.")
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan
)


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
