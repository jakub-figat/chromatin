"""Celery tasks for background job processing"""

import asyncio
import hashlib
import traceback
from contextlib import asynccontextmanager
from typing import Any

import httpx
from Bio import Align
from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from core.celery_app import celery_app
from core.config import settings
from core.exceptions import ValidationError
from jobs import service
from jobs.enums import AlignmentType, JobStatus, JobType
from jobs.schemas import PairwiseAlignmentParams, StructurePredictionParams
from sequences.enums import SequenceType
from sequences.service import (
    get_sequence_data,
    get_sequence_internal,
    get_sequence_structure_internal,
    save_sequence_structure_prediction,
)

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
        elif job.job_type == JobType.STRUCTURE_PREDICTION:
            params = StructurePredictionParams.model_validate(job.params)
            result = await process_structure_prediction(params, db)
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


def _extract_confidence_scores_from_pdb(pdb_content: str) -> list[float]:
    """Parse per-residue confidence (pLDDT) scores from a PDB payload."""
    scores: list[float] = []
    for line in pdb_content.splitlines():
        if not line.startswith(("ATOM", "HETATM")):
            continue
        try:
            score = float(line[60:66].strip())
        except ValueError:
            continue
        scores.append(score)
    return scores


async def _request_esmfold_prediction(sequence: str) -> str:
    """Submit a sequence to the ESMFold API and return the PDB payload."""
    timeout = httpx.Timeout(settings.ESMFOLD_TIMEOUT_SECONDS, connect=30.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                settings.ESMFOLD_API_URL,
                data={"sequence": sequence},
                headers={"Accept": "text/plain"},
            )
            response.raise_for_status()
            return response.text
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        if len(detail) > 200:
            detail = detail[:200] + "..."
        raise ValidationError(
            f"ESMFold API error {exc.response.status_code}: {detail or exc.message}"
        ) from exc
    except httpx.RequestError as exc:
        raise ValidationError(f"ESMFold API request failed: {exc}") from exc


async def process_structure_prediction(
    params: StructurePredictionParams, db: AsyncSession
) -> dict[str, Any]:
    """Process a protein structure prediction job via the ESMFold API."""

    sequence = await get_sequence_internal(params.sequence_id, db)

    if sequence.sequence_type != SequenceType.PROTEIN:
        raise ValidationError(
            "Structure prediction is only supported for protein sequences."
        )

    if sequence.length > settings.ESMFOLD_MAX_RESIDUES:
        raise ValidationError(
            f"Sequence length {sequence.length} exceeds ESMFold limit of {settings.ESMFOLD_MAX_RESIDUES} residues."
        )

    sequence_data = await get_sequence_data(sequence)
    sequence_hash = hashlib.sha256(sequence_data.encode("utf-8")).hexdigest()

    existing_structure = await get_sequence_structure_internal(sequence.id, db)
    if (
        existing_structure
        and existing_structure.sequence_hash == sequence_hash
        and not params.force_recompute
    ):
        return {
            "job_type": "STRUCTURE_PREDICTION",
            "sequence_id": sequence.id,
            "sequence_name": sequence.name,
            "structure_id": existing_structure.id,
            "source": existing_structure.source,
            "cached_result": True,
            "residue_count": existing_structure.residue_count,
            "mean_confidence": existing_structure.mean_confidence,
            "min_confidence": existing_structure.min_confidence,
            "max_confidence": existing_structure.max_confidence,
            "confidence_scores": existing_structure.confidence_scores,
            "pdb_download_path": f"/api/sequences/{sequence.id}/structure/download",
        }

    pdb_content = await _request_esmfold_prediction(sequence_data)
    confidence_scores = _extract_confidence_scores_from_pdb(pdb_content)

    if not confidence_scores:
        raise ValidationError(
            "ESMFold response did not contain residue confidence scores."
        )

    structure = await save_sequence_structure_prediction(
        sequence,
        pdb_content,
        confidence_scores,
        sequence_hash,
        db,
    )

    return {
        "job_type": "STRUCTURE_PREDICTION",
        "sequence_id": sequence.id,
        "sequence_name": sequence.name,
        "structure_id": structure.id,
        "source": structure.source,
        "cached_result": False,
        "residue_count": structure.residue_count,
        "mean_confidence": structure.mean_confidence,
        "min_confidence": structure.min_confidence,
        "max_confidence": structure.max_confidence,
        "confidence_scores": structure.confidence_scores,
        "pdb_download_path": f"/api/sequences/{sequence.id}/structure/download",
    }
