from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import TYPE_CHECKING

from core.config import settings
from core.deps import get_db


if TYPE_CHECKING:
    from common.models import User


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> "User":
    """
    FastAPI dependency to get the current authenticated user

    Usage:
        @router.get("/me")
        async def get_me(current_user: User = Depends(get_current_user)):
            return current_user
    """
    from common.models import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    if (user_id := payload.get("sub")) is None:
        raise credentials_exception

    statement = select(User).where(User.id == int(user_id))
    user = await db.scalar(statement)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user


async def get_current_active_superuser(
    current_user=Depends(get_current_user),
) -> "User":
    """
    Dependency for endpoints that require superuser access

    Usage:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            current_user: User = Depends(get_current_active_superuser)
        ):
            ...
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


async def get_optional_current_user(
    token: str | None = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> "User | None":
    """
    Optional authentication - returns user if token is valid, None otherwise
    Useful for endpoints that work differently for authenticated vs anonymous users

    Usage:
        @router.get("/sequences")
        async def list_sequences(
            current_user: Optional[User] = Depends(get_optional_current_user)
        ):
            # Show public sequences, or user's private ones if authenticated
            ...
    """
    if token is None:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if (user_id := payload.get("sub")) is None:
        raise credentials_exception

    statement = select(User).where(User.id == int(user_id))
    user = await db.scalar(statement)

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )

    return user
