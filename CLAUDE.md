# Expense Tracker API

FastAPI backend for a personal expense-tracking app. REST API consumed by a separate React frontend.

## Stack

- Python 3.10+, FastAPI (run with `fastapi dev app\main.py`)
- SQLAlchemy 2.0 (typed `Mapped[]` style)
- Alembic for migrations
- SQLite in dev, Postgres-ready via `DATABASE_URL` in `.env`
- PyJWT for auth, bcrypt for password hashing
- Pydantic v2 + pydantic-settings

## Commands

- Dev server: `fastapi dev app\main.py`
- New migration: `alembic revision --autogenerate -m "message"`
- Apply migrations: `alembic upgrade head`
- Freeze deps: `pip freeze > requirements.txt`

## Folder layout

- `app/main.py` — FastAPI app, CORS, router includes
- `app/config.py` — Pydantic settings from `.env`
- `app/database.py` — engine, SessionLocal, Base, `get_db` dependency
- `app/models/` — SQLAlchemy models. All models must be imported in `__init__.py`.
- `app/schemas/` — Pydantic request/response schemas
- `app/crud/` — pure DB operation functions
- `app/routers/` — one router file per resource
- `app/core/security.py` — bcrypt + JWT helpers
- `app/core/deps.py` — `get_current_user` dependency

## Conventions

### Models

- SQLAlchemy 2.0 typed style: `Mapped[Type]` + `mapped_column(...)`
- Every user-owned model has `id`, `user_id` (FK to users.id, indexed), `created_at`, `updated_at`
- `created_at` uses `server_default=func.now()`; `updated_at` uses both `server_default=func.now()` and `onupdate=func.now()`
- Use `if TYPE_CHECKING:` for relationship imports to avoid circular imports
- Money fields: `Numeric(precision=12, scale=2)` mapped to `Decimal` — never Float

### Schemas

- One file per resource: `Base`, `Create`, `Update`, `Public` classes
- `Public` includes `model_config = ConfigDict(from_attributes=True)`
- `Update` makes all fields `| None = None` for PATCH semantics

### CRUD

- Pure functions taking `db: Session` and inputs
- Functions reading user-owned data ALWAYS take and filter by `user_id`
- `db.scalar(select(...))` for one row, `db.scalars(...)` for many (wrap in `list()`)

### Routers

- `APIRouter(prefix="/resource", tags=["resource"])`
- Every protected route uses `current_user: User = Depends(get_current_user)`
- Return 404 (not 403) when a user accesses another user's resource — don't reveal existence
- Static path segments (e.g. `/summary`) MUST be declared BEFORE `/{id}` routes

### Migrations

- Always import new models in `app/models/__init__.py` BEFORE `alembic revision --autogenerate`
- Review the generated file before `alembic upgrade head`

## Already implemented

User (with JWT auth and `/auth/login`, `/users/me`), Category (income/expense), Transaction (with date filtering and summary endpoints at `/transactions/summary`, `/summary/by-category`, `/summary/by-month`), CORS configured.
