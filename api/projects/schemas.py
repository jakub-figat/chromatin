from datetime import datetime
from pydantic import Field

from core.schemas import CamelCaseModel


class ProjectInput(CamelCaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    is_public: bool = False


class ProjectOutput(CamelCaseModel):
    id: int
    user_id: int
    name: str
    description: str | None = None
    is_public: bool = False
    created_at: datetime
    updated_at: datetime


class ProjectWithOwner(ProjectOutput):
    owner_email: str
