from pydantic import EmailStr, Field

from core.schemas import CamelCaseModel


class UserBase(CamelCaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(CamelCaseModel):
    email: EmailStr | None = None
    username: str | None = Field(None, min_length=3, max_length=50)
    password: str | None = Field(None, min_length=8)


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool


class Token(CamelCaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(CamelCaseModel):
    user_id: int | None = None
