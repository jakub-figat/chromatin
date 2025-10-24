from pydantic import Field

from core.schemas import CamelCaseModel
from sequences.enums import SequenceType


class SequenceInput(CamelCaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sequence_data: str

    sequence_type: SequenceType
    project_id: int

    description: str | None = Field(None, min_length=1, max_length=255)


class SequenceOutput(CamelCaseModel):
    id: int
    name: str
    sequence_data: str

    sequence_type: SequenceType
    user_id: int
    project_id: int

    description: str | None = None

    length: int
    gc_content: float
    molecular_weight: float


class FastaUploadInput(CamelCaseModel):
    project_id: int
    sequence_type: SequenceType | None = Field(
        None, description="Sequence type. If not provided, will auto-detect."
    )


class FastaUploadOutput(CamelCaseModel):
    sequences_created: int
    sequences: list[SequenceOutput]
