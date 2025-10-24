"""Test authentication endpoints"""

from httpx import AsyncClient


async def test_register_user(client: AsyncClient):
    """Test user registration"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "hashed_password" not in data
    assert data["is_active"] is True
    assert data["is_superuser"] is False


async def test_register_duplicate_email(client: AsyncClient, test_user):
    """Test that registering with duplicate email fails"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": test_user.email,
            "username": "differentuser",
            "password": "password123",
        },
    )

    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


async def test_register_duplicate_username(client: AsyncClient, test_user):
    """Test that registering with duplicate username fails"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "different@example.com",
            "username": test_user.username,
            "password": "password123",
        },
    )

    assert response.status_code == 400
    assert "Username already taken" in response.json()["detail"]


async def test_register_invalid_email(client: AsyncClient):
    """Test registration with invalid email format"""
    response = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "username": "testuser",
            "password": "password123",
        },
    )

    assert response.status_code == 422  # Validation error


async def test_register_short_password(client: AsyncClient):
    """Test registration with too short password"""
    response = await client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "username": "testuser", "password": "short"},
    )

    assert response.status_code == 422


async def test_login_success(client: AsyncClient, test_user):
    """Test successful login"""
    response = await client.post(
        "/api/auth/login", data={"username": test_user.email, "password": "testpass123"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, test_user):
    """Test login with wrong password"""
    response = await client.post(
        "/api/auth/login",
        data={"username": test_user.email, "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent email"""
    response = await client.post(
        "/api/auth/login",
        data={"username": "nonexistent@example.com", "password": "password123"},
    )

    assert response.status_code == 401


async def test_get_current_user(client: AsyncClient, auth_headers):
    """Test getting current user info with valid token"""
    response = await client.get("/api/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert data["is_active"] is True


async def test_get_current_user_no_token(client: AsyncClient):
    """Test that accessing protected endpoint without token fails"""
    response = await client.get("/api/auth/me")

    assert response.status_code == 401


async def test_get_current_user_invalid_token(client: AsyncClient):
    """Test that invalid token is rejected"""
    response = await client.get(
        "/api/auth/me", headers={"Authorization": "Bearer invalid_token_here"}
    )

    assert response.status_code == 401


async def test_get_current_user_malformed_token(client: AsyncClient):
    """Test that malformed token is rejected"""
    response = await client.get(
        "/api/auth/me", headers={"Authorization": "NotBearer token"}
    )

    assert response.status_code == 401
