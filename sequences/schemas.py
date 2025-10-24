from pydantic import BaseModel, Field, ConfigDict

from sequences.enums import SequenceType


class SequenceInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sequence_data: str

    sequence_type: SequenceType
    project_id: int

    description: str | None = Field(None, min_length=1, max_length=255)


class SequenceOutput(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)
