from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from common.service import create_user, authenticate_user
from core.deps import get_db
from core.security import create_access_token, get_current_user
from common import schemas

router = APIRouter()


@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_in: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        user = await create_user(db, user_in)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=schemas.Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = create_access_token(data={"sub": str(user.id)})

    return schemas.Token(access_token=access_token, token_type="bearer")


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Get current user information"""
    return schemas.UserResponse.model_validate(current_user)
