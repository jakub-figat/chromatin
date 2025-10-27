from typing import AsyncIterator
import hashlib

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.dialects.postgresql import insert

from core.consts import MEGABYTE
from common.enums import AccessType
from core.exceptions import ValidationError, NotFoundError
from core.config import settings
from core.storage import get_storage_service
from projects.service import check_project_access
from sequences import Sequence
from sequences.enums import SequenceType
from sequences.fasta_parser import parse_fasta
from sequences.schemas import (
    SequenceInput,
    SequenceOutput,
    SequenceListOutput,
    FastaUploadOutput,
)
from sequences.consts import DNA_CHARS, RNA_CHARS, PROTEIN_CHARS, AMINO_ACID_WEIGHTS
from projects.models import Project
from sequences.utils import validate_sequence_data


async def get_sequence_data(sequence: Sequence) -> str:
    """
    Retrieve the full sequence data, whether stored in DB or file.

    Args:
        sequence: Sequence model instance

    Returns:
        Full sequence data as string

    Raises:
        FileNotFoundError: If file storage is used but file doesn't exist
    """
    if sequence.sequence_data is not None:
        # Stored in database
        return sequence.sequence_data
    elif sequence.file_path:
        # Stored in file
        storage = get_storage_service()
        return await storage.read(sequence.file_path)
    else:
        raise ValueError(f"Sequence {sequence.id} has no data in DB or file storage")


def calculate_gc_content(
    sequence_data: str, sequence_type: SequenceType
) -> float | None:
    """Calculate GC content for DNA/RNA sequences."""
    if sequence_type not in (SequenceType.DNA, SequenceType.RNA):
        return None

    if len(sequence_data) == 0:
        return 0.0

    gc_count = len([base for base in sequence_data.upper() if base in "CG"])
    return gc_count / len(sequence_data)


def calculate_molecular_weight(
    sequence_data: str, sequence_type: SequenceType
) -> float | None:
    """Calculate molecular weight in Daltons (Da) for protein sequences."""
    if sequence_type != SequenceType.PROTEIN:
        return None

    if len(sequence_data) == 0:
        return 0.0

    # Calculate sum of amino acid weights
    total_weight = sum(AMINO_ACID_WEIGHTS[aa] for aa in sequence_data.upper())

    # Subtract water molecules lost during peptide bond formation
    # (n-1) peptide bonds for n amino acids, each bond releases H2O (18.015 Da)
    water_mass = 18.015
    peptide_bonds = len(sequence_data) - 1

    return total_weight - (peptide_bonds * water_mass)


async def create_sequence(
    sequence_input: SequenceInput, user_id: int, db_session: AsyncSession
) -> SequenceOutput:
    """
    Create a single sequence (max 10KB, always stored in database).
    For larger sequences, use FASTA upload endpoint.
    """
    validate_sequence_data(
        sequence_input.sequence_data, expected_type=sequence_input.sequence_type
    )

    stmt = select(Project).where(Project.id == sequence_input.project_id).limit(1)
    db_project = await db_session.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", sequence_input.project_id)

    check_project_access(db_project, user_id, AccessType.WRITE, raise_exception=True)

    # Calculate properties
    seq_length = len(sequence_input.sequence_data)
    gc_content = calculate_gc_content(
        sequence_input.sequence_data, sequence_input.sequence_type
    )
    molecular_weight = calculate_molecular_weight(
        sequence_input.sequence_data, sequence_input.sequence_type
    )

    # Create sequence - always store in DB (size validated by schema)
    db_sequence = Sequence(
        name=sequence_input.name,
        sequence_data=sequence_input.sequence_data,
        file_path=None,
        length=seq_length,
        gc_content=gc_content,
        molecular_weight=molecular_weight,
        sequence_type=sequence_input.sequence_type,
        description=sequence_input.description,
        project_id=sequence_input.project_id,
        user_id=user_id,
    )

    db_session.add(db_sequence)
    await db_session.flush()
    await db_session.refresh(db_sequence)

    return SequenceOutput.model_validate(db_sequence)


async def get_sequence(
    sequence_id: int, user_id: int, db_session: AsyncSession
) -> SequenceOutput:
    stmt = (
        select(Sequence)
        .where(Sequence.id == sequence_id)
        .options(joinedload(Sequence.project))
    )

    db_sequence = await db_session.scalar(stmt)

    if not db_sequence:
        raise NotFoundError("Sequence", sequence_id)

    check_project_access(
        db_sequence.project, user_id, AccessType.READ, raise_exception=True
    )
    return SequenceOutput.model_validate(db_sequence)


async def list_user_sequences(
    user_id: int,
    db_session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    project_id: int | None = None,
    sequence_type: SequenceType | None = None,
    name: str | None = None,
    length_gte: int | None = None,
    length_lte: int | None = None,
) -> list[SequenceListOutput]:
    """
    List all sequences owned by a user with optional filters.
    Returns metadata only (no sequence_data).
    """
    stmt = select(Sequence).where(Sequence.user_id == user_id)

    # Filter by project if provided
    if project_id is not None:
        stmt = stmt.where(Sequence.project_id == project_id)

    # Filter by sequence type if provided
    if sequence_type is not None:
        stmt = stmt.where(Sequence.sequence_type == sequence_type)

    # Filter by name if provided (case-insensitive partial match)
    if name is not None:
        stmt = stmt.where(Sequence.name.ilike(f"%{name}%"))

    # Filter by length range if provided
    if length_gte is not None:
        stmt = stmt.where(Sequence.length >= length_gte)
    if length_lte is not None:
        stmt = stmt.where(Sequence.length <= length_lte)

    stmt = stmt.order_by(Sequence.created_at.desc()).offset(skip).limit(limit)

    results = await db_session.scalars(stmt)
    return [SequenceListOutput.model_validate(sequence) for sequence in results]


async def update_sequence(
    sequence_id: int,
    user_id: int,
    sequence_input: SequenceInput,
    db_session: AsyncSession,
) -> SequenceOutput:
    stmt = (
        select(Sequence)
        .where(Sequence.id == sequence_id)
        .options(joinedload(Sequence.project))
    )

    db_sequence = await db_session.scalar(stmt)

    if not db_sequence:
        raise NotFoundError("Sequence", sequence_id)

    check_project_access(
        db_sequence.project, user_id, AccessType.WRITE, raise_exception=True
    )

    # Validate sequence data if type or data changed
    validate_sequence_data(
        sequence_input.sequence_data, expected_type=sequence_input.sequence_type
    )

    # Check if project is being changed
    if sequence_input.project_id != db_sequence.project_id:
        stmt = select(Project).where(Project.id == sequence_input.project_id)
        new_project = await db_session.scalar(stmt)

        if not new_project:
            raise NotFoundError("Project", sequence_input.project_id)

        check_project_access(
            new_project, user_id, AccessType.WRITE, raise_exception=True
        )

    # Store old file path for cleanup if needed
    old_file_path = db_sequence.file_path

    # Calculate properties
    seq_length = len(sequence_input.sequence_data)
    gc_content = calculate_gc_content(
        sequence_input.sequence_data, sequence_input.sequence_type
    )
    molecular_weight = calculate_molecular_weight(
        sequence_input.sequence_data, sequence_input.sequence_type
    )

    # Update fields - always store in DB (size validated by schema, max 10KB)
    db_sequence.name = sequence_input.name
    db_sequence.sequence_type = sequence_input.sequence_type
    db_sequence.description = sequence_input.description
    db_sequence.project_id = sequence_input.project_id
    db_sequence.length = seq_length
    db_sequence.gc_content = gc_content
    db_sequence.molecular_weight = molecular_weight
    db_sequence.sequence_data = sequence_input.sequence_data
    db_sequence.file_path = None

    # Clean up old file if it existed (update converts file-stored sequences to DB)
    if old_file_path:
        storage = get_storage_service()
        try:
            await storage.delete(old_file_path)
        except Exception:
            # Don't fail update if file cleanup fails
            pass

    await db_session.flush()
    await db_session.refresh(db_sequence)

    return SequenceOutput.model_validate(db_sequence)


async def delete_sequence(
    sequence_id: int, user_id: int, db_session: AsyncSession
) -> None:
    stmt = (
        select(Sequence)
        .where(Sequence.id == sequence_id)
        .options(joinedload(Sequence.project))
    )

    db_sequence = await db_session.scalar(stmt)

    if not db_sequence:
        raise NotFoundError("Sequence", sequence_id)

    check_project_access(
        db_sequence.project, user_id, AccessType.WRITE, raise_exception=True
    )

    # Clean up file storage if used
    if db_sequence.file_path:
        storage = get_storage_service()
        try:
            await storage.delete(db_sequence.file_path)
        except Exception:
            # Don't fail delete if file cleanup fails
            pass

    await db_session.delete(db_sequence)
    await db_session.flush()


async def stream_sequence_download(
    sequence_id: int, user_id: int, db_session: AsyncSession
):
    """
    Async generator that streams sequence data as FASTA format.

    Args:
        sequence_id: Sequence ID
        user_id: User ID for permission checking
        db_session: Database session

    Yields:
        Chunks of FASTA-formatted sequence data as bytes

    Raises:
        NotFoundError: If sequence doesn't exist
        PermissionDeniedError: If user doesn't have read access
    """
    stmt = (
        select(Sequence)
        .where(Sequence.id == sequence_id)
        .options(joinedload(Sequence.project))
    )

    db_sequence = await db_session.scalar(stmt)

    if not db_sequence:
        raise NotFoundError("Sequence", sequence_id)

    check_project_access(
        db_sequence.project, user_id, AccessType.READ, raise_exception=True
    )

    async def _stream_sequence() -> AsyncIterator[bytes]:
        # Yield FASTA header
        header = f">{db_sequence.name}\n"
        yield header.encode("utf-8")

        # Stream sequence data
        if db_sequence.sequence_data is not None:
            # Stored in database - yield directly
            yield db_sequence.sequence_data.encode("utf-8")
        elif db_sequence.file_path:
            # Stored in file - stream in chunks
            storage = get_storage_service()
            async for chunk in await storage.read_chunks(db_sequence.file_path):
                yield chunk
        else:
            raise ValueError(f"Sequence {sequence_id} has no data")

        # Yield final newline
        yield b"\n"

    return _stream_sequence()


async def stream_batch_download(
    sequence_ids: list[int], user_id: int, db_session: AsyncSession
) -> AsyncIterator[bytes]:
    """
    Validate access and return async generator that streams multiple sequences.

    Uses two-phase approach:
    1. Validate all sequences exist and user has access (loads only IDs + projects)
    2. Stream sequences iteratively without loading all into memory

    Args:
        sequence_ids: List of sequence IDs to download
        user_id: User ID for permission checking
        db_session: Database session

    Returns:
        Async iterator that yields chunks of FASTA-formatted data

    Raises:
        NotFoundError: If any sequence doesn't exist
        PermissionDeniedError: If user doesn't have read access to any sequence
    """
    # Phase 1: Validation - fetch only IDs and projects (no sequence_data or file_path)
    validation_stmt = (
        select(Sequence.id, Project)
        .join(Sequence.project)
        .where(Sequence.id.in_(sequence_ids))
    )
    validation_results = await db_session.execute(validation_stmt)
    validation_rows = validation_results.all()

    # Check all sequences exist
    found_ids = {row.id for row in validation_rows}
    missing_ids = set(sequence_ids) - found_ids
    if missing_ids:
        raise NotFoundError("Sequence", f"IDs: {sorted(missing_ids)}")

    # Check permissions for all sequences
    for row in validation_rows:
        project = row.Project
        check_project_access(project, user_id, AccessType.READ, raise_exception=True)

    # Phase 2: Streaming - query all sequences but iterate without loading into list
    async def _stream_sequences() -> AsyncIterator[bytes]:
        storage = get_storage_service()

        # Query all sequences - don't evaluate to list, iterate directly
        sequences_stmt = select(Sequence).where(Sequence.id.in_(sequence_ids))
        sequences_result = await db_session.stream_scalars(sequences_stmt)

        async for db_sequence in sequences_result:
            # Yield FASTA header
            header = f">{db_sequence.name}\n"
            yield header.encode("utf-8")

            # Stream sequence data
            if db_sequence.sequence_data is not None:
                # Stored in database - yield directly
                yield db_sequence.sequence_data.encode("utf-8")
            elif db_sequence.file_path:
                # Stored in file - stream in chunks
                async for chunk in await storage.read_chunks(db_sequence.file_path):
                    yield chunk
            else:
                raise ValueError(f"Sequence {db_sequence.id} has no data")

            # Yield newline between sequences
            yield b"\n"

    return _stream_sequences()


async def upload_fasta(
    files: list[UploadFile],
    project_id: int,
    user_id: int,
    db_session: AsyncSession,
    sequence_type: SequenceType | None = None,
) -> FastaUploadOutput:
    """
    Upload one or more FASTA files and create sequences in a project.

    Processes files sequentially to avoid loading all into memory.
    Uses deterministic filenames (content hash) for idempotency.
    Cleans up storage on transaction rollback.

    Args:
        files: List of UploadFile objects (can be single file)
        project_id: Project to add sequences to
        user_id: User creating the sequences
        db_session: Database session
        sequence_type: Optional sequence type. If not provided, will auto-detect.

    Returns:
        FastaUploadOutput with count of created sequences

    Raises:
        ValidationError: If files exceed size limits or FASTA format is invalid
        NotFoundError: If project doesn't exist
        PermissionDeniedError: If user doesn't have write access to project
    """
    # Check project exists and user has write access (once upfront)
    stmt = select(Project).where(Project.id == project_id)
    db_project = await db_session.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", project_id)

    check_project_access(db_project, user_id, AccessType.WRITE, raise_exception=True)

    total_size = 0
    storage = get_storage_service()
    storage_paths_created = []  # Track for cleanup on failure
    sequence_values = []  # Collect all values for batch upsert

    try:
        # TODO: Frontend should warn users if uploading sequences with conflicting names

        # Process files and collect values
        for file in files:
            # Read and validate file size
            file_content = await file.read()
            file_size = len(file_content)

            if file_size > settings.MAX_FASTA_FILE_SIZE:
                raise ValidationError(
                    f"File '{file.filename}' is too large ({file_size / MEGABYTE:.1f}MB). "
                    f"Maximum file size is {settings.MAX_FASTA_FILE_SIZE / MEGABYTE:.0f}MB."
                )

            total_size += file_size
            if total_size > settings.MAX_FASTA_UPLOAD_TOTAL_SIZE:
                raise ValidationError(
                    f"Total upload size ({total_size / MEGABYTE:.1f}MB) exceeds limit "
                    f"({settings.MAX_FASTA_UPLOAD_TOTAL_SIZE / MEGABYTE:.0f}MB)."
                )

            # Parse FASTA file
            fasta_content = file_content.decode("utf-8")
            try:
                fasta_sequences = parse_fasta(fasta_content)
            except ValidationError as e:
                raise ValidationError(
                    f"File '{file.filename}': FASTA parsing error: {e}"
                )

            # Validate and prepare values for each sequence
            for fasta_seq in fasta_sequences:
                # Validate sequence and determine type
                try:
                    detected_type = validate_sequence_data(
                        fasta_seq.sequence_data, fasta_seq.header, sequence_type
                    )
                except ValidationError as e:
                    raise ValidationError(
                        f"File '{file.filename}', sequence '{fasta_seq.header}': {e}"
                    )

                # Calculate properties
                seq_length = len(fasta_seq.sequence_data)
                gc_content = calculate_gc_content(
                    fasta_seq.sequence_data, detected_type
                )
                molecular_weight = calculate_molecular_weight(
                    fasta_seq.sequence_data, detected_type
                )

                # Determine storage strategy based on size
                sequence_size = len(fasta_seq.sequence_data.encode("utf-8"))

                if sequence_size > settings.SEQUENCE_SIZE_THRESHOLD:
                    # Calculate deterministic filename based on (user_id, name)
                    # This ensures same user + same name = same file (enables overwriting)
                    name_hash = hashlib.sha256(
                        f"{user_id}:{fasta_seq.header}".encode()
                    ).hexdigest()
                    filename = f"{name_hash}.txt"

                    # Large sequence: store in file
                    new_file_path = await storage.save(
                        fasta_seq.sequence_data, filename
                    )
                    storage_paths_created.append(new_file_path)
                    new_sequence_data = None
                else:
                    # Small sequence: store in database
                    new_file_path = None
                    new_sequence_data = fasta_seq.sequence_data

                # Collect values for batch upsert
                sequence_values.append(
                    {
                        "name": fasta_seq.header,
                        "user_id": user_id,
                        "project_id": project_id,
                        "sequence_type": detected_type,
                        "sequence_data": new_sequence_data,
                        "file_path": new_file_path,
                        "length": seq_length,
                        "gc_content": gc_content,
                        "molecular_weight": molecular_weight,
                        "description": fasta_seq.description,
                    }
                )

        # Batch upsert all sequences in a single query
        if sequence_values:
            insert_stmt = insert(Sequence).values(sequence_values)

            # On conflict (user_id, name), update all fields
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=["user_id", "name"],
                set_={
                    "sequence_data": insert_stmt.excluded.sequence_data,
                    "file_path": insert_stmt.excluded.file_path,
                    "length": insert_stmt.excluded.length,
                    "gc_content": insert_stmt.excluded.gc_content,
                    "molecular_weight": insert_stmt.excluded.molecular_weight,
                    "sequence_type": insert_stmt.excluded.sequence_type,
                    "description": insert_stmt.excluded.description,
                    "project_id": insert_stmt.excluded.project_id,
                },
            )

            await db_session.execute(upsert_stmt)
            await db_session.flush()

    except Exception:
        # Cleanup storage files on failure
        for path in storage_paths_created:
            try:
                await storage.delete(path)
            except Exception:
                # Log but don't fail on cleanup errors
                pass
        raise

    return FastaUploadOutput(
        sequences_created=len(sequence_values),
    )
