from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.crud import transfers as transfer_crud
from app.database import get_db
from app.models import User
from app.models.transfer import Transfer
from app.schemas.transfer import TransferCreate, TransferRead, TransferUpdate

router = APIRouter(prefix="/transfers", tags=["transfers"])


def _to_read(t: Transfer) -> TransferRead:
    return TransferRead(
        id=t.id,
        user_id=t.user_id,
        from_account_id=t.from_account_id,
        to_account_id=t.to_account_id,
        amount=t.amount,
        transfer_date=t.transfer_date,
        description=t.description,
        created_at=t.created_at,
        from_account_name=t.from_account.name,
        to_account_name=t.to_account.name,
    )


@router.post("", response_model=TransferRead, status_code=status.HTTP_201_CREATED)
def create_transfer(
    transfer_in: TransferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = transfer_crud.create_transfer(db, transfer_in, current_user.id)
    return _to_read(transfer)


@router.get("", response_model=list[TransferRead])
def list_transfers(
    start_date: date | None = None,
    end_date: date | None = None,
    account_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfers = transfer_crud.get_transfers_for_user(
        db, current_user.id, start_date=start_date, end_date=end_date, account_id=account_id
    )
    return [_to_read(t) for t in transfers]


@router.get("/{transfer_id}", response_model=TransferRead)
def get_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = transfer_crud.get_transfer_for_user(db, transfer_id, current_user.id)
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    return _to_read(transfer)


@router.patch("/{transfer_id}", response_model=TransferRead)
def update_transfer(
    transfer_id: int,
    transfer_in: TransferUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = transfer_crud.get_transfer_for_user(db, transfer_id, current_user.id)
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    transfer = transfer_crud.update_transfer(db, transfer, transfer_in, current_user.id)
    return _to_read(transfer)


@router.delete("/{transfer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transfer(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    transfer = transfer_crud.get_transfer_for_user(db, transfer_id, current_user.id)
    if transfer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transfer not found")
    transfer_crud.delete_transfer(db, transfer)
