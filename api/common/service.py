from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from common import schemas
from common.models import User
from core.security import get_password_hash, verify_password


async def create_user(
    db: AsyncSession, user_in: schemas.UserCreate
) -> schemas.UserResponse:
    stmt = select(User).where(
        (User.email == user_in.email) | (User.username == user_in.username)
    )

    existing_user = await db.scalar(stmt)

    if existing_user:
        if existing_user.email == user_in.email:
            raise ValueError("Email already registered")
        else:
            raise ValueError("Username already taken")

    db_user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        is_active=True,
        is_superuser=False,
    )

    db.add(db_user)
    await db.flush()

    return schemas.UserResponse.model_validate(db_user)


async def authenticate_user(
    db: AsyncSession, email_or_username: str, password: str
) -> User | None:
    """Authenticate a user by email or username and password"""
    stmt = select(User).where(
        (User.email == email_or_username) | (User.username == email_or_username)
    )
    user = await db.scalar(stmt)

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> schemas.UserResponse | None:
    """Get user by ID"""
    stmt = select(User).where(User.id == user_id)
    user = await db.scalar(stmt)

    if not user:
        return None

    return schemas.UserResponse.model_validate(user)


async def get_user_by_email(
    db: AsyncSession, email: str
) -> schemas.UserResponse | None:
    stmt = select(User).where(User.email == email)
    user = await db.scalar(stmt)

    if not user:
        return None

    return schemas.UserResponse.model_validate(user)
