from datetime import datetime
from sqlalchemy import String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, relationship, mapped_column

from common.models import User
from jobs.enums import JobStatus, JobType
from core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    status: Mapped[JobStatus] = mapped_column(default=JobStatus.PENDING)
    job_type: Mapped[JobType]

    # Job parameters (varies by job type)
    params: Mapped[dict | None] = mapped_column(JSONB)

    # Job result (varies by job type)
    result: Mapped[dict | None] = mapped_column(JSONB)

    # Completion tracking
    completed_at: Mapped[datetime | None]

    # Error information
    error_message: Mapped[str | None] = mapped_column(String(1000))

    # Ownership
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # Relationships
    user: Mapped[User] = relationship(back_populates="jobs", lazy="raise")
