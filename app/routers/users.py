from fastapi import APIRouter, HTTPException, Depends, status as Status
from sqlalchemy.orm import Session

from app.crud import user as user_crud
from app.schemas.user import UserCreate, UserPublic
from app.database import get_db


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserPublic, status_code=Status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    existing_user = user_crud.get_user_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )
    db_user = user_crud.create_user(db, user_in)
    return db_user


@router.get("/{user_id}", response_model=UserPublic)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a user by their ID."""
    db_user = user_crud.get_user_by_id(db, user_id)
    if not db_user:
        raise HTTPException(
            status_code=Status.HTTP_404_NOT_FOUND,
            detail="User not found."
        )
    return db_user
