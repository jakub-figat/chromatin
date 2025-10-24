from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import User
from core.deps import get_db
from core.security import get_current_user
from sequences.schemas import SequenceOutput, SequenceInput
from sequences.service import (
    create_sequence,
    get_sequence,
    list_user_sequences,
    list_project_sequences,
    update_sequence,
    delete_sequence,
)

router = APIRouter()


@router.post("/", response_model=SequenceOutput, status_code=status.HTTP_201_CREATED)
async def create_new_sequence(
    sequence_input: SequenceInput,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    return await create_sequence(sequence_input, current_user.id, db_session)


@router.get("/", response_model=list[SequenceOutput])
async def list_sequences(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    return await list_user_sequences(current_user.id, db_session, skip, limit)


@router.get("/project/{project_id}", response_model=list[SequenceOutput])
async def list_sequences_by_project(
    project_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    return await list_project_sequences(
        project_id, current_user.id, db_session, skip, limit
    )


@router.get("/{sequence_id}", response_model=SequenceOutput)
async def get_sequence_detail(
    sequence_id: int,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    return await get_sequence(sequence_id, current_user.id, db_session)


@router.patch("/{sequence_id}", response_model=SequenceOutput)
async def update_sequence_detail(
    sequence_id: int,
    sequence_input: SequenceInput,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    return await update_sequence(
        sequence_id, current_user.id, sequence_input, db_session
    )


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence_endpoint(
    sequence_id: int,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    await delete_sequence(sequence_id, current_user.id, db_session)
