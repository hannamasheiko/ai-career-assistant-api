from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import UserCreate


async def get_user_by_username(
    db: AsyncSession,
    username: str,
) -> User | None:
    """Get user by username."""

    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> User | None:
    """Get user by email."""

    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_username_or_email(
    db: AsyncSession,
    username: str,
    email: str,
) -> User | None:
    """Get user by username or email."""

    result = await db.execute(
        select(User).where(
            or_(
                User.username == username,
                User.email == email,
            )
        )
    )
    return result.scalar_one_or_none()


async def create_user(
    db: AsyncSession,
    data: UserCreate,
) -> User:
    """Create a new user."""

    user = User(
        username=data.username,
        email=str(data.email),
        hashed_password=get_password_hash(data.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | None:
    """Authenticate user by username and password."""

    user = await get_user_by_username(db, username=username)

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user