from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from core.schemas import CamelCaseModel
from jobs.enums import JobStatus, JobType


# Job-specific params schemas (each includes job_type as discriminator)
class PairwiseAlignmentParams(CamelCaseModel):
    """Parameters for pairwise alignment job"""

    job_type: Literal["PAIRWISE_ALIGNMENT"]
    sequence_id_1: int
    sequence_id_2: int


# Union of all job params (discriminated by job_type field)
JobParams = Annotated[
    PairwiseAlignmentParams,  # Extend with | OtherJobParams as more job types are added
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
    result: dict | None

    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

    error_message: str | None
    user_id: int
