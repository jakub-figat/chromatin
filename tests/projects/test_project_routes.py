"""Test project API endpoints"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers):
    """Test creating a project via API"""
    response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={
            "name": "API Project",
            "description": "Created via API",
            "is_public": False,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "API Project"
    assert data["description"] == "Created via API"
    assert data["is_public"] is False
    assert "id" in data


@pytest.mark.asyncio
async def test_create_project_unauthorized(client: AsyncClient):
    """Test creating project without auth fails"""
    response = await client.post(
        "/api/projects/", json={"name": "Unauthorized Project"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_project_invalid_data(client: AsyncClient, auth_headers):
    """Test creating project with invalid data"""
    response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": ""},  # Empty name should fail validation
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, auth_headers):
    """Test listing user's projects"""
    # Create a few projects
    for i in range(3):
        await client.post(
            "/api/projects/", headers=auth_headers, json={"name": f"Project {i}"}
        )

    response = await client.get("/api/projects/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_projects_pagination(client: AsyncClient, auth_headers):
    """Test pagination in project listing"""
    # Create 5 projects
    for i in range(5):
        await client.post(
            "/api/projects/", headers=auth_headers, json={"name": f"Project {i}"}
        )

    response = await client.get(
        "/api/projects/", headers=auth_headers, params={"skip": 0, "limit": 2}
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


@pytest.mark.asyncio
async def test_list_projects_unauthorized(client: AsyncClient):
    """Test listing projects without auth fails"""
    response = await client.get("/api/projects/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, auth_headers):
    """Test getting project details"""
    # Create project
    create_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Detail Project"}
    )
    project_id = create_response.json()["id"]

    # Get project
    response = await client.get(f"/api/projects/{project_id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == project_id
    assert data["name"] == "Detail Project"


@pytest.mark.asyncio
async def test_get_nonexistent_project(client: AsyncClient, auth_headers):
    """Test getting non-existent project returns 404"""
    response = await client.get("/api/projects/99999", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_other_user_private_project(
    client: AsyncClient, auth_headers, superuser_headers
):
    """Test accessing another user's private project returns 403"""
    # Create private project as test_user
    create_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "Private Project", "is_public": False},
    )
    project_id = create_response.json()["id"]

    # Try to access as superuser
    response = await client.get(
        f"/api/projects/{project_id}", headers=superuser_headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_other_user_public_project(
    client: AsyncClient, auth_headers, superuser_headers
):
    """Test accessing another user's public project succeeds"""
    # Create public project as test_user
    create_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "Public Project", "is_public": True},
    )
    project_id = create_response.json()["id"]

    # Access as superuser
    response = await client.get(
        f"/api/projects/{project_id}", headers=superuser_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Public Project"


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, auth_headers):
    """Test updating project"""
    # Create project
    create_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Original Name"}
    )
    project_id = create_response.json()["id"]

    # Update project
    response = await client.patch(
        f"/api/projects/{project_id}",
        headers=auth_headers,
        json={
            "name": "Updated Name",
            "description": "New description",
            "is_public": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New description"
    assert data["is_public"] is True


@pytest.mark.asyncio
async def test_update_project_partial(client: AsyncClient, auth_headers):
    """Test partial update of project"""
    # Create project
    create_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "Original", "description": "Original desc"},
    )
    project_id = create_response.json()["id"]

    # Update only name
    response = await client.patch(
        f"/api/projects/{project_id}", headers=auth_headers, json={"name": "New Name"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["description"] == "Original desc"


@pytest.mark.asyncio
async def test_update_nonexistent_project(client: AsyncClient, auth_headers):
    """Test updating non-existent project returns 404"""
    response = await client.patch(
        "/api/projects/99999", headers=auth_headers, json={"name": "New Name"}
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_other_user_project(
    client: AsyncClient, auth_headers, superuser_headers
):
    """Test updating another user's project returns 403"""
    # Create project as test_user
    create_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "User Project", "is_public": True},
    )
    project_id = create_response.json()["id"]

    # Try to update as superuser
    response = await client.patch(
        f"/api/projects/{project_id}",
        headers=superuser_headers,
        json={"name": "Hacked Name"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, auth_headers):
    """Test deleting project"""
    # Create project
    create_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "To Delete"}
    )
    project_id = create_response.json()["id"]

    # Delete project
    response = await client.delete(f"/api/projects/{project_id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify it's gone
    get_response = await client.get(f"/api/projects/{project_id}", headers=auth_headers)
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent_project(client: AsyncClient, auth_headers):
    """Test deleting non-existent project returns 404"""
    response = await client.delete("/api/projects/99999", headers=auth_headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_other_user_project(
    client: AsyncClient, auth_headers, superuser_headers
):
    """Test deleting another user's project returns 403"""
    # Create project as test_user
    create_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "Protected Project", "is_public": True},
    )
    project_id = create_response.json()["id"]

    # Try to delete as superuser
    response = await client.delete(
        f"/api/projects/{project_id}", headers=superuser_headers
    )

    assert response.status_code == 403
