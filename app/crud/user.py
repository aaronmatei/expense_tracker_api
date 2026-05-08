from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.core.security import hash_password
from app.schemas.user import UserCreate


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Get a user by their ID."""
    return db.scalar(select(User).where(User.id == user_id))


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get a user by their email address."""
    return db.scalar(select(User).where(User.email == email))


def create_user(db: Session, user: UserCreate) -> User:
    """Create a new user in the database."""
    hashed_password = hash_password(user.password)
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        phone_number=user.phone_number,
        id_number=user.id_number,
        address=user.address,
        full_name=user.full_name,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # populates id, created_at, etc. from the DB
    return db_user
