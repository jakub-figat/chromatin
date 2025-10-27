from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import User
from core.deps import get_db
from core.security import get_current_user
from sequences.schemas import (
    SequenceOutput,
    SequenceListOutput,
    SequenceInput,
    FastaUploadOutput,
    BatchDownloadInput,
)
from sequences.service import (
    create_sequence,
    get_sequence,
    list_user_sequences,
    update_sequence,
    delete_sequence,
    upload_fasta,
    stream_sequence_download,
    stream_batch_download,
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


@router.get("/", response_model=list[SequenceListOutput])
async def list_sequences(
    skip: int = 0,
    limit: int = 100,
    project_id: int | None = None,
    sequence_type: SequenceType | None = None,
    name: str | None = None,
    length_gte: int | None = None,
    length_lte: int | None = None,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    List sequences for the current user (metadata only, no sequence data).

    - **skip**: Number of sequences to skip (pagination)
    - **limit**: Maximum number of sequences to return
    - **project_id**: Optional. Filter by project ID
    - **sequence_type**: Optional. Filter by sequence type (DNA, RNA, PROTEIN)
    - **name**: Optional. Filter by sequence name (case-insensitive partial match)
    - **length_gte**: Optional. Filter sequences with length >= this value
    - **length_lte**: Optional. Filter sequences with length <= this value
    """
    return await list_user_sequences(
        current_user.id,
        db_session,
        skip,
        limit,
        project_id,
        sequence_type,
        name,
        length_gte,
        length_lte,
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


@router.get("/{sequence_id}/download")
async def download_sequence(
    sequence_id: int,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Download a sequence as a FASTA file (streaming).

    Works for both database-stored and file-stored sequences.
    """
    # Get the sequence first to extract filename
    seq_data = await get_sequence(sequence_id, current_user.id, db_session)

    # Stream the download
    return StreamingResponse(
        await stream_sequence_download(sequence_id, current_user.id, db_session),
        media_type="text/plain",
        headers={
            "Content-Disposition": f'attachment; filename="{seq_data.name}.fasta"'
        },
    )


@router.post("/download/batch")
async def download_sequences_batch(
    batch_input: BatchDownloadInput,
    current_user: User = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Download multiple sequences as a single FASTA file (streaming).

    - **sequence_ids**: List of sequence IDs to download (max 1000)

    Returns a single FASTA file containing all requested sequences.
    Works for both database-stored and file-stored sequences.
    """

    batch_stream = await stream_batch_download(
        batch_input.sequence_ids, current_user.id, db_session
    )

    # Stream the download
    return StreamingResponse(
        batch_stream,
        media_type="text/plain",
        headers={"Content-Disposition": 'attachment; filename="sequences.fasta"'},
    )


@router.post(
    "/upload/fasta",
    response_model=FastaUploadOutput,
    status_code=status.HTTP_200_OK,
)
async def upload_fasta_files(
    current_user: User = Depends(get_current_user),
    files: list[UploadFile] = File(...),
    project_id: int = Form(...),
    sequence_type: SequenceType | None = Form(None),
    db_session: AsyncSession = Depends(get_db),
):
    """
    Upload one or more FASTA files and create sequences in a project.

    - **files**: One or more FASTA files to upload (each can contain multiple sequences)
    - **project_id**: ID of the project to add sequences to
    - **sequence_type**: Optional sequence type (DNA, RNA, PROTEIN). If not provided, will auto-detect.

    Returns the count of sequences created (not the sequences themselves).
    """
    return await upload_fasta(
        files, project_id, current_user.id, db_session, sequence_type
    )
