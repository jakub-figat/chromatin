import enum


class JobStatus(enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(enum.Enum):
    PAIRWISE_ALIGNMENT = "PAIRWISE_ALIGNMENT"


class AlignmentType(enum.Enum):
    LOCAL = "LOCAL"  # Smith-Waterman
    GLOBAL = "GLOBAL"  # Needleman-Wunsch
