from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from core.security import get_current_user
from common.models import User
from jobs.enums import JobStatus
from . import schemas
from .service import (
    create_job,
    get_job,
    list_user_jobs,
    cancel_job,
    delete_job,
)

router = APIRouter()


@router.post(
    "/", response_model=schemas.JobDetailOutput, status_code=status.HTTP_201_CREATED
)
async def create_new_job(
    job_input: schemas.JobInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new job with validated params"""
    return await create_job(current_user.id, job_input, db)


@router.get("/", response_model=list[schemas.JobListOutput])
async def list_jobs(
    skip: int = 0,
    limit: int = 100,
    status: JobStatus | None = Query(None, description="Filter by job status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all jobs for the current user with optional status filter"""
    return await list_user_jobs(current_user.id, db, skip, limit, status)


@router.get("/{job_id}", response_model=schemas.JobDetailOutput)
async def get_job_detail(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details for a specific job"""
    return await get_job(job_id, current_user.id, db)


@router.post("/{job_id}/cancel", response_model=schemas.JobDetailOutput)
async def cancel_job_endpoint(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending or running job"""
    return await cancel_job(job_id, current_user.id, db)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_endpoint(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a job"""
    await delete_job(job_id, current_user.id, db)
