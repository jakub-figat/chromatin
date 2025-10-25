from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import User
from core.deps import get_db
from core.security import get_current_user
from sequences.schemas import SequenceOutput, SequenceInput, FastaUploadOutput
from sequences.service import (
    create_sequence,
    get_sequence,
    list_user_sequences,
    update_sequence,
    delete_sequence,
    upload_fasta,
)
from sequences.enums import SequenceType

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
    project_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    List sequences for the current user.

    - **skip**: Number of sequences to skip (pagination)
    - **limit**: Maximum number of sequences to return
    - **project_id**: Optional. Filter by project ID
    """
    return await list_user_sequences(
        current_user.id, db_session, skip, limit, project_id
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


@router.post(
    "/upload/fasta",
    response_model=FastaUploadOutput,
    status_code=status.HTTP_201_CREATED,
)
async def upload_fasta_file(
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    project_id: int = Form(...),
    sequence_type: SequenceType | None = Form(None),
    db_session: AsyncSession = Depends(get_db),
):
    print("AAAAAAA")
    """
    Upload a FASTA file and create sequences in a project.

    - **file**: FASTA file to upload
    - **project_id**: ID of the project to add sequences to
    - **sequence_type**: Optional sequence type (DNA, RNA, PROTEIN). If not provided, will auto-detect.
    """
    # Read file content
    content = await file.read()
    fasta_content = content.decode("utf-8")

    return await upload_fasta(
        fasta_content, project_id, current_user.id, db_session, sequence_type
    )
