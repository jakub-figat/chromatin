"""Celery tasks for background job processing"""

import asyncio
import traceback
from contextlib import asynccontextmanager
from typing import Any

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.celery_app import celery_app
from core.config import settings
from jobs import service
from jobs.enums import JobStatus, JobType
from jobs.schemas import PairwiseAlignmentParams

# Create async engine for Celery tasks (separate from FastAPI's engine)
celery_engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
celery_session_maker = async_sessionmaker(
    celery_engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_celery_db():
    """Create a database session for Celery tasks"""
    async with celery_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


class JobTask(Task):
    """Base task class with automatic job status updates"""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure - mark job as failed in database"""
        job_id = args[0] if args else None
        if job_id:
            error_message = (
                f"{exc.__class__.__name__}: {str(exc)}\n{traceback.format_exc()}"
            )
            asyncio.run(self._mark_job_failed(job_id, error_message))

    async def _mark_job_failed(self, job_id: int, error_message: str):
        """Mark job as failed in database"""
        async with get_celery_db() as db:
            await service.mark_job_failed(job_id, error_message, db)
            await db.commit()


@celery_app.task(base=JobTask, bind=True, name="jobs.process_job")
def process_job(self, job_id: int) -> dict[str, Any]:
    """
    Main task for processing a job.
    Dispatches to specific job handlers based on job_type.

    Args:
        job_id: ID of the job to process

    Returns:
        Dictionary with job results
    """
    return asyncio.run(_process_job_async(job_id))


async def _process_job_async(job_id: int) -> dict[str, Any]:
    """Async implementation of job processing"""
    async with get_celery_db() as db:
        # Update status to RUNNING and commit immediately
        await service.update_job_status(job_id, JobStatus.RUNNING, db)

    async with get_celery_db() as db:
        # Get job details (without ownership check - workers process all jobs)
        job = await service.get_job_internal(job_id, db)

        # Dispatch to appropriate handler based on job_type
        if job.job_type == JobType.PAIRWISE_ALIGNMENT:
            params = PairwiseAlignmentParams.model_validate(job.params)
            result = await process_pairwise_alignment(params, db)
        else:
            raise ValueError(f"Unknown job type: {job.job_type}")

        # Mark as completed with result and commit
        await service.mark_job_completed(job_id, result, db)

        return result


async def process_pairwise_alignment(
    params: PairwiseAlignmentParams, db: AsyncSession
) -> dict[str, Any]:
    """
    Process pairwise alignment job.

    Args:
        params: Typed parameters with sequence_id_1 and sequence_id_2
        db: Database session

    Returns:
        Dictionary with alignment results
    """
    # TODO: Implement pairwise alignment using Biopython
    # This is a placeholder - will be implemented in next step

    # Placeholder implementation
    return {
        "sequence_id_1": params.sequence_id_1,
        "sequence_id_2": params.sequence_id_2,
        "alignment_score": 0.0,
        "alignment": "TODO: Implement alignment",
        "message": "Alignment functionality not yet implemented",
    }
