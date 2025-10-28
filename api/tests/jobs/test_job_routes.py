"""Test job API endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from jobs import Job
from jobs.enums import JobStatus


async def test_create_job(client: AsyncClient, auth_headers):
    """Test creating a job via API"""
    response = await client.post(
        "/api/jobs/",
        headers=auth_headers,
        json={
            "params": {
                "jobType": "PAIRWISE_ALIGNMENT",
                "sequenceId1": 1,
                "sequenceId2": 2,
            }
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["jobType"] == "PAIRWISE_ALIGNMENT"
    assert data["status"] == "PENDING"
    assert data["params"]["sequence_id_1"] == 1
    assert data["params"]["sequence_id_2"] == 2
    assert "id" in data


async def test_create_job_unauthorized(client: AsyncClient):
    """Test creating job without auth fails"""
    response = await client.post(
        "/api/jobs/",
        json={
            "params": {
                "jobType": "PAIRWISE_ALIGNMENT",
                "sequenceId1": 1,
                "sequenceId2": 2,
            }
        },
    )

    assert response.status_code == 401


async def test_create_job_invalid_data(client: AsyncClient, auth_headers):
    """Test creating job with invalid data"""
    response = await client.post(
        "/api/jobs/",
        headers=auth_headers,
        json={
            "params": {
                "jobType": "INVALID_TYPE",
                "sequenceId1": 1,
            }
        },
    )

    assert response.status_code == 422


async def test_list_jobs(client: AsyncClient, auth_headers):
    """Test listing user's jobs"""
    # Create a few jobs
    for i in range(3):
        await client.post(
            "/api/jobs/",
            headers=auth_headers,
            json={
                "params": {
                    "jobType": "PAIRWISE_ALIGNMENT",
                    "sequenceId1": i,
                    "sequenceId2": i + 1,
                }
            },
        )

    response = await client.get("/api/jobs/", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


async def test_list_jobs_with_status_filter(
    client: AsyncClient, auth_headers, test_job: Job
):
    """Test listing jobs with status filter"""
    response = await client.get(
        "/api/jobs/",
        headers=auth_headers,
        params={"status": "PENDING"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "PENDING"


async def test_list_jobs_pagination(client: AsyncClient, auth_headers):
    """Test pagination in job listing"""
    # Create 5 jobs
    for i in range(5):
        await client.post(
            "/api/jobs/",
            headers=auth_headers,
            json={
                "params": {
                    "jobType": "PAIRWISE_ALIGNMENT",
                    "sequenceId1": i,
                    "sequenceId2": i + 1,
                }
            },
        )

    response = await client.get(
        "/api/jobs/", headers=auth_headers, params={"skip": 0, "limit": 2}
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_jobs_unauthorized(client: AsyncClient):
    """Test listing jobs without auth fails"""
    response = await client.get("/api/jobs/")

    assert response.status_code == 401


async def test_get_job(client: AsyncClient, auth_headers, test_job: Job):
    """Test getting job details"""
    response = await client.get(f"/api/jobs/{test_job.id}", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_job.id
    assert data["jobType"] == "PAIRWISE_ALIGNMENT"
    assert data["status"] == "PENDING"


async def test_get_nonexistent_job(client: AsyncClient, auth_headers):
    """Test getting non-existent job returns 404"""
    response = await client.get("/api/jobs/99999", headers=auth_headers)

    assert response.status_code == 404


async def test_get_other_user_job(
    client: AsyncClient, superuser_headers, test_job: Job
):
    """Test accessing another user's job returns 404"""
    response = await client.get(f"/api/jobs/{test_job.id}", headers=superuser_headers)

    assert response.status_code == 404


async def test_cancel_job(client: AsyncClient, auth_headers, test_job: Job):
    """Test canceling a job"""
    response = await client.post(
        f"/api/jobs/{test_job.id}/cancel", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
    assert data["completedAt"] is not None


async def test_cancel_nonexistent_job(client: AsyncClient, auth_headers):
    """Test canceling non-existent job returns 404"""
    response = await client.post("/api/jobs/99999/cancel", headers=auth_headers)

    assert response.status_code == 404


async def test_cancel_other_user_job(
    client: AsyncClient, superuser_headers, test_job: Job
):
    """Test canceling another user's job returns 404"""
    response = await client.post(
        f"/api/jobs/{test_job.id}/cancel", headers=superuser_headers
    )

    assert response.status_code == 404


async def test_cancel_completed_job(
    client: AsyncClient, auth_headers, test_session: AsyncSession
):
    """Test canceling a completed job returns 400"""
    # Create job
    create_response = await client.post(
        "/api/jobs/",
        headers=auth_headers,
        json={
            "params": {
                "jobType": "PAIRWISE_ALIGNMENT",
                "sequenceId1": 1,
                "sequenceId2": 2,
            }
        },
    )
    job_id = create_response.json()["id"]

    # Manually mark it as completed
    from jobs.service import mark_job_completed

    await mark_job_completed(job_id, {"result": "done"}, test_session)

    # Try to cancel
    response = await client.post(f"/api/jobs/{job_id}/cancel", headers=auth_headers)

    assert response.status_code == 400
    assert "Cannot cancel" in response.json()["detail"]


async def test_delete_job(client: AsyncClient, auth_headers, test_job: Job):
    """Test deleting a job"""
    response = await client.delete(f"/api/jobs/{test_job.id}", headers=auth_headers)

    assert response.status_code == 204

    # Verify it's gone
    get_response = await client.get(f"/api/jobs/{test_job.id}", headers=auth_headers)
    assert get_response.status_code == 404


async def test_delete_nonexistent_job(client: AsyncClient, auth_headers):
    """Test deleting non-existent job returns 404"""
    response = await client.delete("/api/jobs/99999", headers=auth_headers)

    assert response.status_code == 404


async def test_delete_other_user_job(
    client: AsyncClient, superuser_headers, test_job: Job
):
    """Test deleting another user's job returns 404"""
    response = await client.delete(
        f"/api/jobs/{test_job.id}", headers=superuser_headers
    )

    assert response.status_code == 404
