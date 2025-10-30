from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from core.schemas import CamelCaseModel
from jobs.enums import AlignmentType, JobStatus, JobType


# Job-specific params schemas (each includes job_type as discriminator)
class PairwiseAlignmentParams(CamelCaseModel):
    """Parameters for pairwise alignment job"""

    job_type: Literal["PAIRWISE_ALIGNMENT"]
    sequence_id_1: int
    sequence_id_2: int
    alignment_type: AlignmentType = AlignmentType.GLOBAL

    # Scoring parameters with sensible defaults
    match_score: int = Field(
        default=2, ge=-10, le=10, description="Score for matching residues"
    )
    mismatch_score: int = Field(
        default=-1, ge=-10, le=10, description="Score for mismatched residues"
    )
    gap_open_score: int = Field(
        default=-5, ge=-20, le=0, description="Penalty for opening a gap"
    )
    gap_extend_score: int = Field(
        default=-1, ge=-20, le=0, description="Penalty for extending a gap"
    )


class StructurePredictionParams(CamelCaseModel):
    """Parameters for protein structure prediction job"""

    job_type: Literal["STRUCTURE_PREDICTION"]
    sequence_id: int
    force_recompute: bool = Field(
        default=False,
        description="Force a fresh prediction even if a cached structure exists",
    )


# Union of all job params (discriminated by job_type field)
JobParams = Annotated[
    PairwiseAlignmentParams | StructurePredictionParams,
    Field(discriminator="job_type"),
]


# Job-specific result schemas (each includes job_type as discriminator)
class ScoringParamsResult(CamelCaseModel):
    """Scoring parameters used in alignment"""

    match_score: int
    mismatch_score: int
    gap_open_score: int
    gap_extend_score: int


class PairwiseAlignmentResult(CamelCaseModel):
    """Result from pairwise alignment job"""

    job_type: Literal["PAIRWISE_ALIGNMENT"]

    # Input reference
    sequence_id_1: int
    sequence_id_2: int
    sequence_name_1: str
    sequence_name_2: str

    # Alignment configuration
    alignment_type: str  # "GLOBAL" or "LOCAL"

    # Alignment results
    alignment_score: float
    aligned_seq_1: str
    aligned_seq_2: str

    # Statistics
    alignment_length: int
    matches: int
    mismatches: int
    gaps: int
    identity_percent: float

    # Representations
    cigar: str
    scoring_params: ScoringParamsResult


class StructurePredictionResult(CamelCaseModel):
    """Result from protein structure prediction job"""

    job_type: Literal["STRUCTURE_PREDICTION"]

    sequence_id: int
    sequence_name: str
    structure_id: int

    source: str
    cached_result: bool

    residue_count: int
    mean_confidence: float
    min_confidence: float
    max_confidence: float

    confidence_scores: list[float]
    pdb_download_path: str


# Union of all job results (discriminated by job_type field)
JobResult = Annotated[
    PairwiseAlignmentResult | StructurePredictionResult,
    Field(discriminator="job_type"),
]


class JobInput(CamelCaseModel):
    """Schema for creating a new job"""

    params: JobParams


class JobListOutput(CamelCaseModel):
    """Schema for listing jobs - excludes large result data"""

    id: int
    status: JobStatus
    job_type: JobType

    # Include params for reference but not full result
    params: dict | None

    created_at: datetime
    completed_at: datetime | None

    error_message: str | None


class JobDetailOutput(CamelCaseModel):
    """Schema for job details - includes full result"""

    id: int
    status: JobStatus
    job_type: JobType

    params: dict | None
    result: JobResult | None

    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    error_message: str | None
    user_id: int
