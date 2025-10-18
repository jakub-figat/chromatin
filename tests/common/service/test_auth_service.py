"""Test authentication service functions"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import User
from common.service import (
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email,
)
from common.schemas import UserCreate


@pytest.mark.asyncio
async def test_create_user(test_session: AsyncSession):
    """Test creating a user"""
    user_in = UserCreate(
        email="newuser@example.com", username="newuser", password="password123"
    )

    user = await create_user(test_session, user_in)

    assert user.id is not None
    assert user.email == "newuser@example.com"
    assert user.username == "newuser"
    assert user.is_active is True
    assert user.is_superuser is False


@pytest.mark.asyncio
async def test_create_user_duplicate_email(test_session: AsyncSession, test_user):
    """Test that creating user with duplicate email raises error"""
    user_in = UserCreate(
        email=test_user.email,  # Duplicate
        username="differentuser",
        password="password123",
    )

    with pytest.raises(ValueError, match="Email already registered"):
        await create_user(test_session, user_in)


@pytest.mark.asyncio
async def test_create_user_duplicate_username(test_session: AsyncSession, test_user):
    """Test that creating user with duplicate username raises error"""
    user_in = UserCreate(
        email="different@example.com",
        username=test_user.username,  # Duplicate
        password="password123",
    )

    with pytest.raises(ValueError, match="Username already taken"):
        await create_user(test_session, user_in)


@pytest.mark.asyncio
async def test_authenticate_user_success(test_session: AsyncSession, test_user):
    """Test successful authentication"""
    user = await authenticate_user(test_session, test_user.email, "testpass123")

    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(test_session: AsyncSession, test_user):
    """Test authentication with wrong password"""
    user = await authenticate_user(test_session, test_user.email, "wrongpassword")

    assert user is None


@pytest.mark.asyncio
async def test_authenticate_user_nonexistent_email(test_session: AsyncSession):
    """Test authentication with non-existent email"""
    user = await authenticate_user(
        test_session, "nonexistent@example.com", "password123"
    )

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_id(test_session: AsyncSession, test_user):
    """Test getting user by ID"""
    user = await get_user_by_id(test_session, test_user.id)

    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email
    assert user.username == test_user.username


@pytest.mark.asyncio
async def test_get_user_by_id_not_found(test_session: AsyncSession):
    """Test getting non-existent user by ID"""
    user = await get_user_by_id(test_session, 99999)

    assert user is None


@pytest.mark.asyncio
async def test_get_user_by_email(test_session: AsyncSession, test_user):
    """Test getting user by email"""
    user = await get_user_by_email(test_session, test_user.email)

    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_user_by_email_not_found(test_session: AsyncSession):
    """Test getting non-existent user by email"""
    user = await get_user_by_email(test_session, "nonexistent@example.com")

    assert user is None
