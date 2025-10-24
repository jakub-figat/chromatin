from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from core.security import get_current_user
from common.models import User
from . import schemas
from .service import (
    create_project,
    get_project,
    list_user_projects,
    update_project,
    delete_project,
)

router = APIRouter()


@router.post(
    "/", response_model=schemas.ProjectOutput, status_code=status.HTTP_201_CREATED
)
async def create_new_project(
    project_input: schemas.ProjectInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_project(db, current_user.id, project_input)


@router.get("/", response_model=list[schemas.ProjectOutput])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_user_projects(db, current_user.id, skip, limit)


@router.get("/{project_id}", response_model=schemas.ProjectOutput)
async def get_project_detail(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_project(db, project_id, current_user.id)


@router.patch("/{project_id}", response_model=schemas.ProjectOutput)
async def update_project_detail(
    project_id: int,
    project_input: schemas.ProjectInput,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await update_project(db, project_id, current_user.id, project_input)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_endpoint(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_project(db, project_id, current_user.id)
