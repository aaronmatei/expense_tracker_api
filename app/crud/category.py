from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def list_categories(db: Session, user_id: int) -> list[Category]:
    return list(
        db.scalars(
            select(Category)
            .where(Category.user_id == user_id)
            .order_by(Category.name)
        )
    )


def get_category(db: Session, category_id: int, user_id: int) -> Category | None:
    return db.scalar(select(Category).where(
        Category.id == category_id,
        Category.user_id == user_id
    ))


def create_category(db: Session, category_in: CategoryCreate, user_id: int) -> Category:
    db_category = Category(**category_in.model_dump(), user_id=user_id)
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


def update_category(
    db: Session,
    category: Category,
    category_in: CategoryUpdate,
) -> Category:
    update_data = category_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(category, key, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    db.delete(category)
    db.commit()
