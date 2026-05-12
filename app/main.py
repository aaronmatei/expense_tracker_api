from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import employee  # noqa: F401
from app.models import recurring_transaction  # noqa: F401
from app.models import transfer  # noqa: F401
from app.routers import accounts, auth, budgets, categories, employees, recurring_transactions, transactions, transfers, users

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(categories.router)
app.include_router(transactions.router)
app.include_router(budgets.router)
app.include_router(accounts.router)
app.include_router(employees.router)
app.include_router(recurring_transactions.router)
app.include_router(transfers.router)


@app.get("/")
def read_root():
    return {
        "status": "ok",
        "message": f"{settings.app_name} is running",
        "environment": settings.environment,
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
