from datetime import date

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import employees as employee_crud
from app.database import get_db
from app.models import User
from app.models.transaction import Transaction
from app.schemas.employee import (
    BulkPayRequest,
    BulkPayResponse,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    PayEmployeeRequest,
)
from app.schemas.transaction import TransactionPublic

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    employee_in: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return employee_crud.create_employee(db, employee_in, current_user.id)


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return employee_crud.get_employees_for_user(
        db, current_user.id, is_active=is_active, search=search
    )


# Static routes BEFORE /{employee_id}
@router.get("/due", response_model=list[EmployeeRead])
def get_due_employees(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return employee_crud.get_due_employees(db, current_user.id, date.today())


@router.post("/pay-bulk", response_model=BulkPayResponse)
def pay_bulk(
    bulk_in: BulkPayRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return employee_crud.pay_employees_bulk(db, bulk_in, current_user.id)


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return employee_crud.get_employee_for_user(db, employee_id, current_user.id)


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: int,
    employee_in: EmployeeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = employee_crud.get_employee_for_user(db, employee_id, current_user.id)
    return employee_crud.update_employee(db, employee, employee_in)


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = employee_crud.get_employee_for_user(db, employee_id, current_user.id)
    has_transactions = db.scalar(
        select(Transaction).where(Transaction.employee_id == employee.id).limit(1)
    )
    if has_transactions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot delete employee with existing transactions. "
                "Set is_active to false to deactivate."
            ),
        )
    employee_crud.delete_employee(db, employee)


@router.post("/{employee_id}/pay", response_model=TransactionPublic)
def mark_employee_paid(
    employee_id: int,
    payload: PayEmployeeRequest = Body(default=PayEmployeeRequest()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    employee = employee_crud.get_employee_for_user(db, employee_id, current_user.id)
    return employee_crud.mark_employee_paid(db, employee, payload, current_user.id)
