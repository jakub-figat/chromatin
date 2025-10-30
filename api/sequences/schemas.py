from datetime import datetime
from pydantic import Field, field_validator

from core.schemas import CamelCaseModel
from sequences.enums import SequenceType


class SequenceInput(CamelCaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sequence_data: str = Field(
        ..., max_length=10000
    )  # Max 10KB for single sequence POST

    sequence_type: SequenceType
    project_id: int

    description: str | None = Field(None, max_length=255)

    @field_validator("sequence_data")
    @classmethod
    def validate_sequence_size(cls, v: str) -> str:
        # Enforce max size in bytes (10KB)
        size_bytes = len(v.encode("utf-8"))
        if size_bytes > 10000:
            raise ValueError(
                f"Sequence too large ({size_bytes} bytes). "
                f"Maximum size is 10KB. Use FASTA upload for larger sequences."
            )
        return v


class SequenceListOutput(CamelCaseModel):
    """Schema for list endpoint - never includes sequence_data"""

    id: int
    name: str

    sequence_type: SequenceType
    user_id: int
    project_id: int

    description: str | None = None

    length: int
    gc_content: float | None
    molecular_weight: float | None

    uses_file_storage: bool  # True if sequence is stored in file

    created_at: datetime
    updated_at: datetime


class SequenceDetailOutput(CamelCaseModel):
    """Schema for detail endpoint - includes sequence_data only if stored in DB"""

    id: int
    name: str
    sequence_data: str | None  # Only present if stored in DB (not file)

    sequence_type: SequenceType
    user_id: int
    project_id: int

    description: str | None = None

    length: int
    gc_content: float | None
    molecular_weight: float | None

    uses_file_storage: bool  # True if sequence is stored in file

    created_at: datetime
    updated_at: datetime


# Alias for backwards compatibility
SequenceOutput = SequenceDetailOutput


class SequenceStructureOutput(CamelCaseModel):
    """Metadata for a stored protein structure prediction."""

    id: int
    sequence_id: int
    sequence_name: str
    source: str
    residue_count: int
    mean_confidence: float
    min_confidence: float
    max_confidence: float
    confidence_scores: list[float]
    created_at: datetime
    updated_at: datetime
    download_path: str


class FastaUploadInput(CamelCaseModel):
    project_id: int
    sequence_type: SequenceType | None = Field(
        None, description="Sequence type. If not provided, will auto-detect."
    )


class FastaUploadOutput(CamelCaseModel):
    sequences_created: int


class BatchDownloadInput(CamelCaseModel):
    sequence_ids: list[int] = Field(..., min_length=1, max_length=1000)
