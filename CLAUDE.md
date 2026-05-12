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

User (with JWT auth and `/auth/login`, `/users/me`), Category (income/expense), Transaction (with date filtering and summary endpoints at `/transactions/summary`, `/summary/by-category`, `/summary/by-month`), CORS configured, Employee (full CRUD + payroll scheduling).

## Payroll

### pay_day_config shapes (stored as JSON)

| `pay_frequency`  | Required shape |
|------------------|----------------|
| `monthly`        | `{"day": 1–31}` — values > 28 clamp to last day of short months |
| `semi_monthly`   | `{"days": [v1, v2]}` — each value is int 1–31 or the string `"last"` |
| `weekly`         | `{"weekday": "monday"\|…\|"sunday"}` |
| `biweekly`       | `{"weekday": "monday"\|…", "anchor_date": "YYYY-MM-DD"}` — anchor establishes the 14-day cycle |

All computed pay dates are weekend-adjusted: Saturday → Friday, Sunday → Monday.

### Pay date helpers — `app/services/payroll.py`

- `compute_pay_dates_for_month(year, month, frequency, config)` — all adjusted dates in a month
- `get_most_recent_pay_date(today, frequency, config, start_date)` — most recent date ≤ today ≥ start_date
- `get_next_pay_date(after, frequency, config, start_date)` — next date strictly after `after`
- `is_due_for_pay(employee, today)` — True if a pay date has passed since `last_paid_date` (or `start_date` if never paid)

### Delete rule

`DELETE /employees/{id}` returns **409 Conflict** if any transactions reference that employee. Use `PATCH /employees/{id}` with `{"is_active": false}` to deactivate instead.

### Bulk pay — `POST /employees/pay-bulk`

- Each payment is wrapped in a savepoint (`db.begin_nested()`).
- One failure does **not** roll back the whole batch — only that payment's savepoint is rolled back.
- Response shape: `{ "successful": [TransactionPublic], "failed": [{"employee_id": int, "error": str}] }`.

### Seed note

The seeded category is named **"Payroll"** (not "Employees"). This rename only applies to fresh seed data — existing user data is not auto-migrated.
