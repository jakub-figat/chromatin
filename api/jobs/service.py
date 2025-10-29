from datetime import datetime, UTC

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.celery_app import celery_app
from core.exceptions import NotFoundError, ValidationError
from jobs import models, schemas
from jobs.enums import JobStatus, JobType


def check_job_ownership(job: models.Job, user_id: int) -> None:
    """Check if user owns the job, raise exception if not"""
    if job.user_id != user_id:
        raise NotFoundError("Job", job.id)


async def create_job(
    user_id: int, job_input: schemas.JobInput, db: AsyncSession
) -> schemas.JobDetailOutput:
    """Create a new job with PENDING status and dispatch to Celery"""
    db_job = models.Job(
        job_type=JobType(job_input.params.job_type),
        params=job_input.params.model_dump(mode="json"),
        status=JobStatus.PENDING,
        user_id=user_id,
    )

    db.add(db_job)
    await db.flush()
    await db.refresh(db_job)

    # Dispatch job to Celery worker with job_id as task_id for easy revocation
    celery_app.send_task("jobs.process_job", args=[db_job.id], task_id=str(db_job.id))

    return schemas.JobDetailOutput.model_validate(db_job)


async def get_job(
    job_id: int, user_id: int, db: AsyncSession
) -> schemas.JobDetailOutput:
    """Get a single job by ID with ownership check"""
    stmt = select(models.Job).where(models.Job.id == job_id)
    job = await db.scalar(stmt)

    if not job:
        raise NotFoundError("Job", job_id)

    check_job_ownership(job, user_id)

    return schemas.JobDetailOutput.model_validate(job)


async def get_job_internal(job_id: int, db: AsyncSession) -> models.Job:
    """Get a job by ID without ownership check (for internal/worker use)"""
    stmt = select(models.Job).where(models.Job.id == job_id)
    job = await db.scalar(stmt)

    if not job:
        raise NotFoundError("Job", job_id)

    return job


async def list_user_jobs(
    user_id: int,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    status: JobStatus | None = None,
) -> list[schemas.JobListOutput]:
    """List all jobs for a user with optional status filter"""
    stmt = (
        select(models.Job)
        .where(models.Job.user_id == user_id)
        .order_by(models.Job.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if status:
        stmt = stmt.where(models.Job.status == status)

    results = await db.scalars(stmt)
    return [schemas.JobListOutput.model_validate(job) for job in results]


async def update_job_status(
    job_id: int, status: JobStatus, db: AsyncSession
) -> schemas.JobDetailOutput:
    """Update job status (used by background workers)"""
    stmt = select(models.Job).where(models.Job.id == job_id)
    job = await db.scalar(stmt)

    if not job:
        raise NotFoundError("Job", job_id)

    job.status = status

    await db.flush()
    await db.refresh(job)

    return schemas.JobDetailOutput.model_validate(job)


async def mark_job_completed(
    job_id: int, result: dict, db: AsyncSession
) -> schemas.JobDetailOutput:
    """Mark a job as completed with result data"""
    stmt = select(models.Job).where(models.Job.id == job_id)
    job = await db.scalar(stmt)

    if not job:
        raise NotFoundError("Job", job_id)

    job.status = JobStatus.COMPLETED
    job.result = result
    job.completed_at = datetime.now()

    await db.flush()
    await db.refresh(job)

    return schemas.JobDetailOutput.model_validate(job)


async def mark_job_failed(
    job_id: int, error_message: str, db: AsyncSession
) -> schemas.JobDetailOutput:
    """Mark a job as failed with error message"""
    stmt = select(models.Job).where(models.Job.id == job_id)
    job = await db.scalar(stmt)

    if not job:
        raise NotFoundError("Job", job_id)

    job.status = JobStatus.FAILED
    job.error_message = error_message
    job.completed_at = datetime.now()

    await db.flush()
    await db.refresh(job)

    return schemas.JobDetailOutput.model_validate(job)


async def cancel_job(
    job_id: int, user_id: int, db: AsyncSession
) -> schemas.JobDetailOutput:
    """Cancel a pending or running job and revoke the Celery task"""
    stmt = select(models.Job).where(models.Job.id == job_id)
    job = await db.scalar(stmt)

    if not job:
        raise NotFoundError("Job", job_id)

    check_job_ownership(job, user_id)

    if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
        raise ValidationError(
            f"Cannot cancel job with status {job.status.value}. "
            "Only PENDING or RUNNING jobs can be cancelled."
        )

    # Revoke the Celery task (terminate=True kills running tasks)
    celery_app.control.revoke(str(job_id), terminate=True)

    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now()

    await db.flush()
    await db.refresh(job)

    return schemas.JobDetailOutput.model_validate(job)


async def delete_job(job_id: int, user_id: int, db: AsyncSession) -> None:
    """Delete a job and revoke its Celery task if running (only if owned by user)"""
    stmt = select(models.Job).where(models.Job.id == job_id)
    job = await db.scalar(stmt)

    if not job:
        raise NotFoundError("Job", job_id)

    check_job_ownership(job, user_id)

    # Revoke the Celery task if it's still pending or running
    if job.status in [JobStatus.PENDING, JobStatus.RUNNING]:
        celery_app.control.revoke(str(job_id), terminate=True)

    await db.delete(job)
    await db.flush()
