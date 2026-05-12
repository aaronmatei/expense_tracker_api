from datetime import date

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import recurring_transactions as rt_crud
from app.database import get_db
from app.models import User
from app.models.category import CategoryType
from app.schemas.recurring_transaction import (
    BulkMaterializeRequest,
    BulkMaterializeResponse,
    MaterializeRequest,
    RecurringTransactionCreate,
    RecurringTransactionRead,
    RecurringTransactionUpdate,
)
from app.schemas.transaction import TransactionPublic

router = APIRouter(prefix="/recurring-transactions", tags=["recurring-transactions"])


@router.post("", response_model=RecurringTransactionRead, status_code=status.HTTP_201_CREATED)
def create(
    payload: RecurringTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rt_crud.create(db, payload, current_user.id)


@router.get("", response_model=list[RecurringTransactionRead])
def list_templates(
    is_active: bool | None = Query(default=None),
    type: CategoryType | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rt_crud.list_for_user(db, current_user.id, is_active=is_active, transaction_type=type)


# Static routes BEFORE /{recurring_transaction_id}
@router.get("/due", response_model=list[RecurringTransactionRead])
def get_due(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rt_crud.get_due_for_user(db, current_user.id, date.today())


@router.post("/materialize-bulk", response_model=BulkMaterializeResponse)
def materialize_bulk(
    payload: BulkMaterializeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rt_crud.materialize_bulk(db, payload, current_user.id)


@router.get("/{recurring_transaction_id}", response_model=RecurringTransactionRead)
def get_one(
    recurring_transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return rt_crud.get_for_user(db, recurring_transaction_id, current_user.id)


@router.patch("/{recurring_transaction_id}", response_model=RecurringTransactionRead)
def update(
    recurring_transaction_id: int,
    payload: RecurringTransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = rt_crud.get_for_user(db, recurring_transaction_id, current_user.id)
    return rt_crud.update(db, template, payload, current_user.id)


@router.delete("/{recurring_transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    recurring_transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = rt_crud.get_for_user(db, recurring_transaction_id, current_user.id)
    rt_crud.delete(db, template)


@router.post(
    "/{recurring_transaction_id}/materialize",
    response_model=TransactionPublic,
)
def materialize(
    recurring_transaction_id: int,
    payload: MaterializeRequest = Body(default=MaterializeRequest()),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    template = rt_crud.get_for_user(db, recurring_transaction_id, current_user.id)
    return rt_crud.materialize(db, template, payload, current_user.id)
