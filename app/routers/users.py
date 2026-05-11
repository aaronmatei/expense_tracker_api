from fastapi import APIRouter, HTTPException, Depends, status as Status
from sqlalchemy.orm import Session

from app.crud import user as user_crud
from app.schemas.user import UserCreate, UserPublic, UserUpdate, ChangePasswordRequest
from app.database import get_db
from app.models import User
from app.core.deps import get_current_user
from app.core.security import verify_password


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


@router.get("/me", response_model=UserPublic)
def get_current_user(current_user: User = Depends(get_current_user)):
    """Get the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserPublic)
def update_current_user(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return user_crud.update_user(db, current_user, user_in)


@router.post("/me/password", status_code=Status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=Status.HTTP_400_BAD_REQUEST, detail="Incorrect current password")
    user_crud.change_password(db, current_user, body.new_password)


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
