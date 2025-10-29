"""Celery tasks for background job processing"""

import asyncio
import traceback
from contextlib import asynccontextmanager
from typing import Any

from Bio import Align
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.celery_app import celery_app
from core.config import settings
from core.exceptions import ValidationError
from jobs import service
from jobs.enums import AlignmentType, JobStatus, JobType
from jobs.schemas import PairwiseAlignmentParams
from sequences.service import get_sequence_data, get_sequence_internal

# Create async engine for Celery tasks (separate from FastAPI's engine)
# Use NullPool to avoid connection reuse issues with asyncio.run() in workers
celery_engine = create_async_engine(
    settings.DATABASE_URL, echo=settings.DEBUG, poolclass=NullPool
)
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
        await db.commit()

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
        await db.commit()

        return result


def _generate_cigar(aligned_seq1: str, aligned_seq2: str) -> str:
    """
    Generate CIGAR string from aligned sequences.

    Args:
        aligned_seq1: First aligned sequence (with gaps as '-')
        aligned_seq2: Second aligned sequence (with gaps as '-')

    Returns:
        CIGAR string (e.g., "5M2I3M1D2M")

    Format:
        M = Match/Mismatch
        I = Insertion in seq1 (gap in seq2)
        D = Deletion in seq1 (gap in seq1)
    """
    cigar = []
    current_op = None
    count = 0

    for base1, base2 in zip(aligned_seq1, aligned_seq2):
        if base1 == "-":
            # Deletion (gap in seq1)
            op = "D"
        elif base2 == "-":
            # Insertion (gap in seq2)
            op = "I"
        else:
            # Match or mismatch
            op = "M"

        if op == current_op:
            count += 1
        else:
            if current_op is not None:
                cigar.append(f"{count}{current_op}")
            current_op = op
            count = 1

    # Add final operation
    if current_op is not None:
        cigar.append(f"{count}{current_op}")

    return "".join(cigar)


def _calculate_alignment_stats(aligned_seq1: str, aligned_seq2: str) -> dict[str, Any]:
    """
    Calculate detailed alignment statistics.

    Args:
        aligned_seq1: First aligned sequence (with gaps)
        aligned_seq2: Second aligned sequence (with gaps)

    Returns:
        Dictionary with alignment statistics
    """
    matches = 0
    mismatches = 0
    gaps = 0
    alignment_length = len(aligned_seq1)

    for base1, base2 in zip(aligned_seq1, aligned_seq2):
        if base1 == "-" or base2 == "-":
            gaps += 1
        elif base1 == base2:
            matches += 1
        else:
            mismatches += 1

    # Calculate identity percentage (matches / non-gap positions)
    non_gap_length = alignment_length - gaps
    identity_percent = (matches / non_gap_length * 100) if non_gap_length > 0 else 0.0

    return {
        "alignment_length": alignment_length,
        "matches": matches,
        "mismatches": mismatches,
        "gaps": gaps,
        "identity_percent": round(identity_percent, 2),
    }


async def process_pairwise_alignment(
    params: PairwiseAlignmentParams, db: AsyncSession
) -> dict[str, Any]:
    """
    Process pairwise alignment job using Biopython.

    Supports both local (Smith-Waterman) and global (Needleman-Wunsch) alignment
    with configurable scoring parameters.

    Args:
        params: Typed parameters including:
            - sequence_id_1, sequence_id_2: Sequences to align
            - alignment_type: LOCAL or GLOBAL
            - match_score, mismatch_score, gap_open_score, gap_extend_score

        db: Database session

    Returns:
        Dictionary with comprehensive alignment results:
            - aligned_seq_1, aligned_seq_2: Aligned sequences with gaps
            - alignment_score: Numeric alignment score
            - identity_percent: Percentage of matching positions
            - matches, mismatches, gaps: Detailed statistics
            - alignment_length: Total length including gaps
            - cigar: CIGAR string representation
            - alignment_type: Type of alignment performed

    Raises:
        NotFoundError: If sequences don't exist
        ValidationError: If sequences are incompatible (e.g., different types)
    """
    # Fetch sequences (without ownership check - workers process all jobs)
    seq1 = await get_sequence_internal(params.sequence_id_1, db)
    seq2 = await get_sequence_internal(params.sequence_id_2, db)

    # Validate sequences are compatible types
    if seq1.sequence_type != seq2.sequence_type:
        raise ValidationError(
            f"Cannot align sequences of different types: "
            f"{seq1.sequence_type.value} vs {seq2.sequence_type.value}"
        )

    # Get sequence data (handles both DB and file storage)
    seq1_data = await get_sequence_data(seq1)
    seq2_data = await get_sequence_data(seq2)

    # Configure Biopython aligner
    aligner = Align.PairwiseAligner()

    # Set alignment mode
    if params.alignment_type == AlignmentType.LOCAL:
        aligner.mode = "local"
    else:  # GLOBAL
        aligner.mode = "global"

    # Set scoring parameters
    aligner.match_score = params.match_score
    aligner.mismatch_score = params.mismatch_score
    aligner.open_gap_score = params.gap_open_score
    aligner.extend_gap_score = params.gap_extend_score

    # Perform alignment
    alignments = aligner.align(seq1_data, seq2_data)

    # Get best alignment (first one has highest score)
    best_alignment = alignments[0]

    # Extract aligned sequences (using proper indexing)
    aligned_seq1 = str(best_alignment[0])
    aligned_seq2 = str(best_alignment[1])

    # Calculate statistics
    stats = _calculate_alignment_stats(aligned_seq1, aligned_seq2)

    # Generate CIGAR string
    cigar = _generate_cigar(aligned_seq1, aligned_seq2)

    # Return comprehensive results
    return {
        "job_type": "PAIRWISE_ALIGNMENT",  # Required for discriminated union
        "sequence_id_1": params.sequence_id_1,
        "sequence_id_2": params.sequence_id_2,
        "sequence_name_1": seq1.name,
        "sequence_name_2": seq2.name,
        "alignment_type": params.alignment_type.value,
        "alignment_score": float(best_alignment.score),
        "aligned_seq_1": aligned_seq1,
        "aligned_seq_2": aligned_seq2,
        "alignment_length": stats["alignment_length"],
        "matches": stats["matches"],
        "mismatches": stats["mismatches"],
        "gaps": stats["gaps"],
        "identity_percent": stats["identity_percent"],
        "cigar": cigar,
        "scoring_params": {
            "match_score": params.match_score,
            "mismatch_score": params.mismatch_score,
            "gap_open_score": params.gap_open_score,
            "gap_extend_score": params.gap_extend_score,
        },
    }
