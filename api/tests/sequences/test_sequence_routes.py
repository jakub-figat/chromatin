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
    assert data["sequenceData"] == "ATGCATGC"
    assert data["sequenceType"] == "DNA"
    assert data["length"] == 8
    assert data["gcContent"] == 0.5
    assert "id" in data


async def test_list_sequences(client: AsyncClient, auth_headers):
    """Test listing all user sequences"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create multiple sequences
    for i in range(3):
        await client.post(
            "/api/sequences/",
            headers=auth_headers,
            json={
                "name": f"seq_{i}",
                "sequence_type": "DNA",
                "sequence_data": "ATGC",
                "project_id": project_id,
            },
        )

    # List all sequences
    response = await client.get("/api/sequences/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all(seq["userId"] == response.headers.get("x-user-id") for seq in data if "x-user-id" in response.headers)


async def test_list_sequences_filtered_by_project(client: AsyncClient, auth_headers):
    """Test listing sequences filtered by project_id"""
    # Create two projects
    project1_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Project 1"}
    )
    project1_id = project1_response.json()["id"]

    project2_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Project 2"}
    )
    project2_id = project2_response.json()["id"]

    # Create sequences in project 1
    for i in range(2):
        await client.post(
            "/api/sequences/",
            headers=auth_headers,
            json={
                "name": f"proj1_seq_{i}",
                "sequence_type": "DNA",
                "sequence_data": "ATGC",
                "project_id": project1_id,
            },
        )

    # Create sequences in project 2
    for i in range(3):
        await client.post(
            "/api/sequences/",
            headers=auth_headers,
            json={
                "name": f"proj2_seq_{i}",
                "sequence_type": "DNA",
                "sequence_data": "ATGC",
                "project_id": project2_id,
            },
        )

    # Filter by project 1
    response = await client.get(
        f"/api/sequences/?project_id={project1_id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(seq["projectId"] == project1_id for seq in data)

    # Filter by project 2
    response = await client.get(
        f"/api/sequences/?project_id={project2_id}", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all(seq["projectId"] == project2_id for seq in data)


async def test_list_sequences_pagination(client: AsyncClient, auth_headers):
    """Test listing sequences with pagination"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create 5 sequences
    for i in range(5):
        await client.post(
            "/api/sequences/",
            headers=auth_headers,
            json={
                "name": f"seq_{i}",
                "sequence_type": "DNA",
                "sequence_data": "ATGC",
                "project_id": project_id,
            },
        )

    # Get first 2
    response = await client.get("/api/sequences/?limit=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Skip first 2, get next 2
    response = await client.get("/api/sequences/?skip=2&limit=2", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


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
    assert data["sequenceData"] == "ATGCATGC"
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


# FASTA upload tests


async def test_upload_fasta_single_sequence(client: AsyncClient, auth_headers):
    """Test uploading FASTA file with single sequence"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "FASTA Project"}
    )
    project_id = project_response.json()["id"]

    # Create FASTA file content
    fasta_content = ">test_seq Test DNA sequence\nACGTACGT"

    # Upload FASTA
    response = await client.post(
        "/api/sequences/upload/fasta",
        headers=auth_headers,
        files={"file": ("test.fasta", fasta_content, "text/plain")},
        data={"project_id": project_id, "sequence_type": "DNA"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sequencesCreated"] == 1
    assert len(data["sequences"]) == 1
    assert data["sequences"][0]["name"] == "test_seq"
    assert data["sequences"][0]["sequenceData"] == "ACGTACGT"
    assert data["sequences"][0]["sequenceType"] == "DNA"
    assert data["sequences"][0]["description"] == "Test DNA sequence"


async def test_upload_fasta_multiple_sequences(client: AsyncClient, auth_headers):
    """Test uploading FASTA file with multiple sequences"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Multi FASTA Project"}
    )
    project_id = project_response.json()["id"]

    # Create FASTA file with 3 sequences
    fasta_content = """
>seq1 First sequence
ACGT
TGCA
>seq2 Second sequence
GGGGCCCC
>seq3
ATATATATAT
    """.strip()

    # Upload FASTA
    response = await client.post(
        "/api/sequences/upload/fasta",
        headers=auth_headers,
        files={"file": ("multi.fasta", fasta_content, "text/plain")},
        data={"project_id": project_id, "sequence_type": "DNA"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sequencesCreated"] == 3
    assert len(data["sequences"]) == 3
    assert data["sequences"][0]["name"] == "seq1"
    assert data["sequences"][0]["sequenceData"] == "ACGTTGCA"
    assert data["sequences"][1]["name"] == "seq2"
    assert data["sequences"][1]["sequenceData"] == "GGGGCCCC"
    assert data["sequences"][2]["name"] == "seq3"
    assert data["sequences"][2]["description"] is None


async def test_upload_fasta_auto_detect_type(client: AsyncClient, auth_headers):
    """Test uploading FASTA with auto-detection of sequence type"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Auto Detect Project"}
    )
    project_id = project_response.json()["id"]

    # Create FASTA with protein sequence (auto-detect should identify it)
    fasta_content = ">protein_seq Test protein\nMKLLIVLLVAL"

    # Upload without specifying sequence_type
    response = await client.post(
        "/api/sequences/upload/fasta",
        headers=auth_headers,
        files={"file": ("protein.fasta", fasta_content, "text/plain")},
        data={"project_id": project_id},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sequencesCreated"] == 1
    assert data["sequences"][0]["sequenceType"] == "PROTEIN"


async def test_upload_fasta_unauthorized(client: AsyncClient):
    """Test uploading FASTA without authentication fails"""
    fasta_content = ">seq1\nACGT"

    response = await client.post(
        "/api/sequences/upload/fasta",
        files={"file": ("test.fasta", fasta_content, "text/plain")},
        data={"project_id": 1},
    )

    assert response.status_code == 401


async def test_upload_fasta_nonexistent_project(client: AsyncClient, auth_headers):
    """Test uploading FASTA to non-existent project fails"""
    fasta_content = ">seq1\nACGT"

    response = await client.post(
        "/api/sequences/upload/fasta",
        headers=auth_headers,
        files={"file": ("test.fasta", fasta_content, "text/plain")},
        data={"project_id": 99999, "sequence_type": "DNA"},
    )

    assert response.status_code == 404


async def test_upload_fasta_private_project_permission_denied(
    client: AsyncClient, auth_headers, superuser_headers
):
    """Test uploading FASTA to another user's private project fails"""
    # Create private project as test_user
    project_response = await client.post(
        "/api/projects/",
        headers=auth_headers,
        json={"name": "Private Project", "is_public": False},
    )
    project_id = project_response.json()["id"]

    fasta_content = ">seq1\nACGT"

    # Try to upload as superuser
    response = await client.post(
        "/api/sequences/upload/fasta",
        headers=superuser_headers,
        files={"file": ("test.fasta", fasta_content, "text/plain")},
        data={"project_id": project_id, "sequence_type": "DNA"},
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "fasta_content,error_pattern",
    [
        ("", "FASTA file is empty"),
        ("ACGT", "Sequence data found before header"),
        (">seq1", "has no sequence data"),
        (">seq1\nACGTXYZ", "invalid characters"),  # Invalid DNA characters
    ],
)
async def test_upload_fasta_invalid_format(
    client: AsyncClient, auth_headers, fasta_content, error_pattern
):
    """Test uploading FASTA with invalid format fails"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    response = await client.post(
        "/api/sequences/upload/fasta",
        headers=auth_headers,
        files={"file": ("invalid.fasta", fasta_content, "text/plain")},
        data={"project_id": project_id, "sequence_type": "DNA"},
    )

    assert response.status_code == 400


async def test_upload_fasta_type_mismatch(client: AsyncClient, auth_headers):
    """Test uploading FASTA with sequence type mismatch fails"""
    # Create project
    project_response = await client.post(
        "/api/projects/", headers=auth_headers, json={"name": "Test Project"}
    )
    project_id = project_response.json()["id"]

    # Create DNA sequence but specify RNA type
    fasta_content = ">seq1\nACGT"

    response = await client.post(
        "/api/sequences/upload/fasta",
        headers=auth_headers,
        files={"file": ("test.fasta", fasta_content, "text/plain")},
        data={"project_id": project_id, "sequence_type": "RNA"},
    )

    assert response.status_code == 400
