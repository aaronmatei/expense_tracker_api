from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.transaction import _assert_balance_ok, _signed_delta
from app.models.account import Account
from app.models.category import Category
from app.models.employee import Employee
from app.models.transaction import Transaction
from app.schemas.employee import (
    BulkPayError,
    BulkPayRequest,
    BulkPayResponse,
    EmployeeCreate,
    EmployeeUpdate,
    PayEmployeeRequest,
)


def create_employee(db: Session, payload: EmployeeCreate, user_id: int) -> Employee:
    employee = Employee(**payload.model_dump(), user_id=user_id)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee


def get_employee_for_user(db: Session, employee_id: int, user_id: int) -> Employee:
    """Return the employee or raise 404 — never reveals cross-user existence."""
    employee = db.scalar(
        select(Employee).where(
            Employee.id == employee_id, Employee.user_id == user_id
        )
    )
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found"
        )
    return employee


def get_employees_for_user(
    db: Session,
    user_id: int,
    is_active: bool | None = None,
    search: str | None = None,
) -> list[Employee]:
    stmt = select(Employee).where(Employee.user_id == user_id)
    if is_active is not None:
        stmt = stmt.where(Employee.is_active == is_active)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            Employee.first_name.ilike(pattern) | Employee.last_name.ilike(pattern)
        )
    stmt = stmt.order_by(Employee.last_name, Employee.first_name)
    return list(db.scalars(stmt))


def update_employee(db: Session, employee: Employee, payload: EmployeeUpdate) -> Employee:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee: Employee) -> None:
    db.delete(employee)
    db.commit()


def _stage_employee_payment(
    db: Session,
    employee: Employee,
    payload: PayEmployeeRequest,
    user_id: int,
) -> Transaction:
    """Validate and stage a payroll transaction + last_paid_date update. No commit."""
    today = date.today()
    full_name = f"{employee.first_name} {employee.last_name}"

    amount_resolved: Decimal | None = payload.amount if payload.amount is not None else employee.pay_amount
    if amount_resolved is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount is required — this employee has no default pay amount.",
        )
    amount: Decimal = amount_resolved
    account_id: int | None = payload.account_id if payload.account_id is not None else employee.default_account_id
    category_id: int | None = payload.category_id if payload.category_id is not None else employee.default_category_id
    transaction_date: date = payload.transaction_date if payload.transaction_date is not None else today
    description: str = (
        payload.description if payload.description is not None else f"Payroll: {full_name}"
    )

    if account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No account specified and employee has no default account",
        )
    if category_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No category specified and employee has no default category",
        )

    category = db.get(Category, category_id)
    account = db.get(Account, account_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Category not found"
        )
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found"
        )

    delta = _signed_delta(amount, category)
    _assert_balance_ok(account, delta)

    tx = Transaction(
        amount=amount,
        description=description,
        transaction_date=transaction_date,
        category_id=category_id,
        account_id=account_id,
        user_id=user_id,
        employee_id=employee.id,
    )
    db.add(tx)
    account.current_balance += delta
    employee.last_paid_date = transaction_date
    return tx


def mark_employee_paid(
    db: Session,
    employee: Employee,
    payload: PayEmployeeRequest,
    user_id: int,
) -> Transaction:
    tx = _stage_employee_payment(db, employee, payload, user_id)
    db.commit()
    db.refresh(tx)
    return tx


def pay_employees_bulk(
    db: Session, payload: BulkPayRequest, user_id: int
) -> BulkPayResponse:
    from fastapi import HTTPException as _HTTPException

    successful: list[Transaction] = []
    failed: list[BulkPayError] = []

    for item in payload.payments:
        savepoint = db.begin_nested()
        try:
            employee = get_employee_for_user(db, item.employee_id, user_id)
            pay_req = PayEmployeeRequest(
                amount=item.amount,
                transaction_date=item.transaction_date,
                account_id=item.account_id,
                category_id=item.category_id,
                description=item.description,
            )
            tx = _stage_employee_payment(db, employee, pay_req, user_id)
            db.flush()
            savepoint.commit()
            successful.append(tx)
        except Exception as exc:
            savepoint.rollback()
            error_msg = exc.detail if isinstance(exc, _HTTPException) else str(exc)
            failed.append(BulkPayError(employee_id=item.employee_id, error=error_msg))

    if successful:
        db.commit()
        for tx in successful:
            db.refresh(tx)

    return BulkPayResponse(successful=successful, failed=failed)


def get_due_employees(db: Session, user_id: int, today: date) -> list[Employee]:
    from app.services.payroll import is_due_for_pay

    active = get_employees_for_user(db, user_id, is_active=True)
    return [emp for emp in active if is_due_for_pay(emp, today)]
