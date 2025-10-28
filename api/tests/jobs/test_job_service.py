import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import User
from core.exceptions import NotFoundError, ValidationError
from jobs import Job
from jobs.enums import JobStatus, JobType
from jobs.service import (
    create_job,
    get_job,
    list_user_jobs,
    update_job_status,
    mark_job_completed,
    mark_job_failed,
    cancel_job,
    delete_job,
)
from jobs.schemas import JobInput, PairwiseAlignmentParams


async def test_create_job(test_session: AsyncSession, test_user: User):
    """Test creating a new job"""
    job_input = JobInput(
        params=PairwiseAlignmentParams(
            job_type=JobType.PAIRWISE_ALIGNMENT.value,
            sequence_id_1=1,
            sequence_id_2=2,
        )
    )

    job = await create_job(test_user.id, job_input, test_session)

    assert job.id is not None
    assert job.job_type == JobType.PAIRWISE_ALIGNMENT
    assert job.status == JobStatus.PENDING
    assert job.params["sequence_id_1"] == 1
    assert job.params["sequence_id_2"] == 2
    assert job.user_id == test_user.id
    assert job.result is None
    assert job.error_message is None


async def test_get_job_as_owner(
    test_session: AsyncSession, test_user: User, test_job: Job
):
    """Test getting a job as the owner"""
    job = await get_job(test_job.id, test_user.id, test_session)

    assert job.id == test_job.id
    assert job.job_type == JobType.PAIRWISE_ALIGNMENT
    assert job.status == JobStatus.PENDING


async def test_get_job_as_other_user(
    test_session: AsyncSession, test_user_2: User, test_job: Job
):
    """Test getting another user's job raises NotFoundError"""
    with pytest.raises(NotFoundError):
        await get_job(test_job.id, test_user_2.id, test_session)


async def test_get_nonexistent_job(test_session: AsyncSession, test_user: User):
    """Test getting non-existent job raises NotFoundError"""
    with pytest.raises(NotFoundError):
        await get_job(99999, test_user.id, test_session)


async def test_list_user_jobs(test_session: AsyncSession, test_user: User):
    """Test listing user jobs"""
    for i in range(3):
        job_input = JobInput(
            params=PairwiseAlignmentParams(
                job_type=JobType.PAIRWISE_ALIGNMENT.value,
                sequence_id_1=i,
                sequence_id_2=i + 1,
            )
        )
        await create_job(test_user.id, job_input, test_session)

    jobs = await list_user_jobs(test_user.id, test_session)

    assert len(jobs) == 3


async def test_list_user_jobs_with_status_filter(
    test_session: AsyncSession, test_user: User, test_job: Job
):
    """Test listing jobs with status filter"""
    # Create another job
    job_input = JobInput(
        params=PairwiseAlignmentParams(
            job_type=JobType.PAIRWISE_ALIGNMENT.value,
            sequence_id_1=3,
            sequence_id_2=4,
        )
    )
    job2 = await create_job(test_user.id, job_input, test_session)

    # Update test_job to RUNNING
    await update_job_status(test_job.id, JobStatus.RUNNING, test_session)

    # Filter by PENDING
    pending_jobs = await list_user_jobs(
        test_user.id, test_session, status=JobStatus.PENDING
    )
    assert len(pending_jobs) == 1
    assert pending_jobs[0].id == job2.id

    # Filter by RUNNING
    running_jobs = await list_user_jobs(
        test_user.id, test_session, status=JobStatus.RUNNING
    )
    assert len(running_jobs) == 1
    assert running_jobs[0].id == test_job.id


async def test_list_user_jobs_pagination(test_session: AsyncSession, test_user: User):
    """Test pagination in job listing"""
    for i in range(5):
        job_input = JobInput(
            params=PairwiseAlignmentParams(
                job_type=JobType.PAIRWISE_ALIGNMENT.value,
                sequence_id_1=i,
                sequence_id_2=i + 1,
            )
        )
        await create_job(test_user.id, job_input, test_session)

    page1 = await list_user_jobs(test_user.id, test_session, skip=0, limit=2)
    assert len(page1) == 2

    page2 = await list_user_jobs(test_user.id, test_session, skip=2, limit=2)
    assert len(page2) == 2

    assert page1[0].id != page2[0].id


async def test_list_user_jobs_empty(test_session: AsyncSession, test_user_2: User):
    """Test listing jobs when user has none"""
    jobs = await list_user_jobs(test_user_2.id, test_session)

    assert len(jobs) == 0


async def test_update_job_status(test_session: AsyncSession, test_job: Job):
    """Test updating job status"""
    updated = await update_job_status(test_job.id, JobStatus.RUNNING, test_session)

    assert updated.status == JobStatus.RUNNING
    assert updated.id == test_job.id


async def test_mark_job_completed(test_session: AsyncSession, test_job: Job):
    """Test marking job as completed"""
    result = {"alignment": "ATGC", "score": 42.5}
    completed = await mark_job_completed(test_job.id, result, test_session)

    assert completed.status == JobStatus.COMPLETED
    assert completed.result == result
    assert completed.completed_at is not None


async def test_mark_job_failed(test_session: AsyncSession, test_job: Job):
    """Test marking job as failed"""
    error_message = "Sequence not found"
    failed = await mark_job_failed(test_job.id, error_message, test_session)

    assert failed.status == JobStatus.FAILED
    assert failed.error_message == error_message
    assert failed.completed_at is not None


async def test_cancel_pending_job(
    test_session: AsyncSession, test_user: User, test_job: Job
):
    """Test canceling a pending job"""
    cancelled = await cancel_job(test_job.id, test_user.id, test_session)

    assert cancelled.status == JobStatus.CANCELLED
    assert cancelled.completed_at is not None


async def test_cancel_running_job(
    test_session: AsyncSession, test_user: User, test_job: Job
):
    """Test canceling a running job"""
    await update_job_status(test_job.id, JobStatus.RUNNING, test_session)

    cancelled = await cancel_job(test_job.id, test_user.id, test_session)

    assert cancelled.status == JobStatus.CANCELLED


async def test_cancel_completed_job_fails(
    test_session: AsyncSession, test_user: User, test_job: Job
):
    """Test canceling a completed job raises ValidationError"""
    await mark_job_completed(test_job.id, {"result": "done"}, test_session)

    with pytest.raises(ValidationError) as exc_info:
        await cancel_job(test_job.id, test_user.id, test_session)

    assert "Cannot cancel" in str(exc_info.value)


async def test_cancel_other_user_job(
    test_session: AsyncSession, test_user_2: User, test_job: Job
):
    """Test canceling another user's job raises NotFoundError"""
    with pytest.raises(NotFoundError):
        await cancel_job(test_job.id, test_user_2.id, test_session)


async def test_delete_job(test_session: AsyncSession, test_user: User, test_job: Job):
    """Test deleting a job"""
    await delete_job(test_job.id, test_user.id, test_session)

    # Verify it's deleted
    with pytest.raises(NotFoundError):
        await get_job(test_job.id, test_user.id, test_session)


async def test_delete_other_user_job(
    test_session: AsyncSession, test_user_2: User, test_job: Job
):
    """Test deleting another user's job raises NotFoundError"""
    with pytest.raises(NotFoundError):
        await delete_job(test_job.id, test_user_2.id, test_session)


async def test_delete_nonexistent_job(test_session: AsyncSession, test_user: User):
    """Test deleting non-existent job raises NotFoundError"""
    with pytest.raises(NotFoundError):
        await delete_job(99999, test_user.id, test_session)
