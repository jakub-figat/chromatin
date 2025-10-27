from datetime import datetime

from core.schemas import CamelCaseModel
from jobs.enums import JobStatus, JobType


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
