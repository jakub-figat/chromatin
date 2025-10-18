from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    is_public: bool = False


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    is_public: bool | None = None


class ProjectResponse(ProjectBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class ProjectWithOwner(ProjectResponse):
    owner_email: str
