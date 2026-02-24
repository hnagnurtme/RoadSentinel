from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.email == email)
        .options(selectinload(User.organization))
    )
    return result.scalar_one_or_none()


async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.organization))
    )
    return result.scalar_one_or_none()


async def create(
    db: AsyncSession,
    *,
    email: str,
    hashed_password: str,
    full_name: str,
    organization_id: int | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        organization_id=organization_id,
    )
    db.add(user)
    await db.flush()  # get user.id without committing
    await db.refresh(user, ["organization"])
    return user
