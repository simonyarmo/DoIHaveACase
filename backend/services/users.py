import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User


async def get_or_create_local_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID | str,
    email: str,
    full_name: str | None,
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is not None:
        return user

    user = User(id=user_id, email=email, full_name=full_name or email)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent first-login from the same user raced us to the insert.
        await db.rollback()
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()
    else:
        await db.refresh(user)

    return user
