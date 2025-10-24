from pydantic import BaseModel, ConfigDict, Field


class ProjectInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    is_public: bool = False


class ProjectOutput(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None = None
    is_public: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProjectWithOwner(ProjectOutput):
    owner_email: str
