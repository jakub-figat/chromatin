"""Test sequence API endpoints"""

import pytest
from httpx import AsyncClient


async def test_create_sequence(client: AsyncClient, auth_headers):
    """Test creating a sequence via API"""
    # First create a project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create sequence
    response = await client.post(
        "/api/sequences/",
        headers=auth_headers,
        json={
            "name": "test_sequence",
            "sequence_type": "DNA",
            "sequence_data": "ATGCATGC",
            "description": "Test DNA sequence",
            "project_id": project_id,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test_sequence"
    assert data["sequence_data"] == "ATGCATGC"
    assert data["sequence_type"] == "DNA"
    assert data["length"] == 8
    assert data["gc_content"] == 0.5
    assert "id" in data


async def test_create_sequence_unauthorized(client: AsyncClient):
    """Test creating sequence without auth fails"""
    response = await client.post(
        "/api/sequences/",
        json={
            "name": "unauthorized",
            "sequence_type": "DNA",
            "sequence_data": "ATGC",
            "project_id": 1,
        },
    )

    assert response.status_code == 401


@pytest.mark.parametrize(
    "sequence_type,sequence_data",
    [
        ("DNA", "ATGCXYZ"),  # Invalid DNA characters
        ("RNA", "AUGCT"),  # T is invalid in RNA
        ("PROTEIN", "ACDEFGXYZ"),  # X, Z not in standard amino acids
    ],
)
async def test_create_sequence_invalid_data(
    client: AsyncClient, auth_headers, sequence_type, sequence_data
):
    """Test creating sequence with invalid sequence data"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Try to create sequence with invalid data
    response = await client.post(
        "/api/sequences/",
        headers=auth_headers,
        json={
            "name": "invalid_sequence",
            "sequence_type": sequence_type,
            "sequence_data": sequence_data,
            "project_id": project_id,
        },
    )

    assert response.status_code == 400


async def test_get_sequence_in_private_project_fails(
    client: AsyncClient, auth_headers, superuser_headers
):
    """Test accessing sequence in another user's private project fails"""
    # Create private project and sequence as test_user
    project_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "Private Project", "is_public": False},
    )
    project_id = project_response.json()["id"]

    create_response = await client.post(
        "/api/sequences/",
        headers=auth_headers,
        json={
            "name": "private_sequence",
            "sequence_type": "DNA",
            "sequence_data": "ATGC",
            "project_id": project_id,
        },
    )
    sequence_id = create_response.json()["id"]

    # Try to access as superuser
    response = await client.get(
        f"/api/sequences/{sequence_id}", headers=superuser_headers
    )

    assert response.status_code == 404


async def test_get_sequence_in_public_project_succeeds(
    client: AsyncClient, auth_headers, superuser_headers
):
    """Test accessing sequence in another user's public project succeeds"""
    # Create public project and sequence as test_user
    project_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "Public Project", "is_public": True},
    )
    project_id = project_response.json()["id"]

    create_response = await client.post(
        "/api/sequences/",
        headers=auth_headers,
        json={
            "name": "public_sequence",
            "sequence_type": "DNA",
            "sequence_data": "ATGC",
            "project_id": project_id,
        },
    )
    sequence_id = create_response.json()["id"]

    # Access as superuser
    response = await client.get(
        f"/api/sequences/{sequence_id}", headers=superuser_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "public_sequence"


async def test_update_sequence(client: AsyncClient, auth_headers):
    """Test updating sequence"""
    # Create project and sequence
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await client.post(
        "/api/sequences/",
        headers=auth_headers,
        json={
            "name": "original_name",
            "sequence_type": "DNA",
            "sequence_data": "ATGC",
            "project_id": project_id,
        },
    )
    sequence_id = create_response.json()["id"]

    # Update sequence
    response = await client.patch(
        f"/api/sequences/{sequence_id}",
        headers=auth_headers,
        json={
            "name": "updated_name",
            "sequence_type": "DNA",
            "sequence_data": "ATGCATGC",
            "description": "Updated",
            "project_id": project_id,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "updated_name"
    assert data["sequence_data"] == "ATGCATGC"
    assert data["description"] == "Updated"
    assert data["length"] == 8


async def test_update_nonexistent_sequence(client: AsyncClient, auth_headers):
    """Test updating non-existent sequence returns 404"""
    response = await client.patch(
        "/api/sequences/99999",
        headers=auth_headers,
        json={
            "name": "test",
            "sequence_type": "DNA",
            "sequence_data": "ATGC",
            "project_id": 1,
        },
    )

    assert response.status_code == 404


async def test_delete_sequence(client: AsyncClient, auth_headers):
    """Test deleting sequence"""
    # Create project and sequence
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    create_response = await client.post(
        "/api/sequences/",
        headers=auth_headers,
        json={
            "name": "to_delete",
            "sequence_type": "DNA",
            "sequence_data": "ATGC",
            "project_id": project_id,
        },
    )
    sequence_id = create_response.json()["id"]

    # Delete sequence
    response = await client.delete(
        f"/api/sequences/{sequence_id}", headers=auth_headers
    )

    assert response.status_code == 204

    # Verify it's gone
    get_response = await client.get(
        f"/api/sequences/{sequence_id}", headers=auth_headers
    )
    assert get_response.status_code == 404


async def test_delete_nonexistent_sequence(client: AsyncClient, auth_headers):
    """Test deleting non-existent sequence returns 404"""
    response = await client.delete("/api/sequences/99999", headers=auth_headers)

    assert response.status_code == 404
