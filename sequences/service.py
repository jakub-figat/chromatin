from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from common.enums import AccessType
from core.exceptions import ValidationError, NotFoundError, PermissionDeniedError
from projects.service import check_project_access
from sequences import Sequence
from sequences.enums import SequenceType
from sequences.schemas import SequenceInput, SequenceOutput, FastaUploadOutput
from sequences.consts import DNA_CHARS, RNA_CHARS, PROTEIN_CHARS
from sequences.fasta_parser import parse_fasta, validate_fasta_sequence
from projects.models import Project


def check_sequence_is_valid(sequence_data: str, seq_type: SequenceType) -> bool:
    sequence_upper = sequence_data.upper()
    sequence_set = set(sequence_upper)

    if seq_type == SequenceType.DNA:
        return sequence_set.issubset(DNA_CHARS)
    elif seq_type == SequenceType.RNA:
        return sequence_set.issubset(RNA_CHARS)
    elif seq_type == SequenceType.PROTEIN:
        return sequence_set.issubset(PROTEIN_CHARS)

    return False


async def create_sequence(
    sequence_input: SequenceInput, user_id: int, db_session: AsyncSession
) -> SequenceOutput:
    if not check_sequence_is_valid(
        sequence_input.sequence_data, sequence_input.sequence_type
    ):
        raise ValidationError(
            f"Invalid sequence of type {sequence_input.sequence_type}"
        )

    stmt = select(Project).where(Project.id == sequence_input.project_id).limit(1)
    db_project = await db_session.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", sequence_input.project_id)

    check_project_access(db_project, user_id, AccessType.WRITE, raise_exception=True)

    db_sequence = Sequence(**sequence_input.model_dump(), user_id=user_id)
    db_session.add(db_sequence)
    await db_session.flush()

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
    user_id: int, db_session: AsyncSession, skip: int = 0, limit: int = 100
) -> list[SequenceOutput]:
    """List all sequences owned by a user"""
    stmt = (
        select(Sequence)
        .where(Sequence.user_id == user_id)
        .order_by(Sequence.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    results = await db_session.scalars(stmt)
    return [SequenceOutput.model_validate(sequence) for sequence in results]


async def list_project_sequences(
    project_id: int,
    user_id: int,
    db_session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[SequenceOutput]:
    """List all sequences in a project (if user has access)"""
    # First check if user has access to the project
    stmt = select(Project).where(Project.id == project_id)
    db_project = await db_session.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", project_id)

    check_project_access(db_project, user_id, AccessType.READ, raise_exception=True)

    # Get sequences
    stmt = (
        select(Sequence)
        .where(Sequence.project_id == project_id)
        .order_by(Sequence.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    results = await db_session.scalars(stmt)
    return [SequenceOutput.model_validate(sequence) for sequence in results]


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
    if not check_sequence_is_valid(
        sequence_input.sequence_data, sequence_input.sequence_type
    ):
        raise ValidationError(
            f"Invalid sequence of type {sequence_input.sequence_type}"
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

    # Update fields
    db_sequence.name = sequence_input.name
    db_sequence.sequence_data = sequence_input.sequence_data
    db_sequence.sequence_type = sequence_input.sequence_type
    db_sequence.description = sequence_input.description
    db_sequence.project_id = sequence_input.project_id

    await db_session.flush()

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

    await db_session.delete(db_sequence)
    await db_session.flush()


async def upload_fasta(
    fasta_content: str,
    project_id: int,
    user_id: int,
    db_session: AsyncSession,
    sequence_type: SequenceType | None = None,
) -> FastaUploadOutput:
    """
    Upload and parse a FASTA file, creating multiple sequences.

    Args:
        fasta_content: Content of the FASTA file
        project_id: Project to add sequences to
        user_id: User creating the sequences
        db_session: Database session
        sequence_type: Optional sequence type. If not provided, will auto-detect.

    Returns:
        FastaUploadOutput with created sequences

    Raises:
        ValidationError: If FASTA format is invalid or sequences are invalid
        NotFoundError: If project doesn't exist
        PermissionDeniedError: If user doesn't have write access to project
    """
    # Check project exists and user has write access
    stmt = select(Project).where(Project.id == project_id)
    db_project = await db_session.scalar(stmt)

    if not db_project:
        raise NotFoundError("Project", project_id)

    check_project_access(db_project, user_id, AccessType.WRITE, raise_exception=True)

    # Parse FASTA file
    try:
        fasta_sequences = parse_fasta(fasta_content)
    except ValidationError as e:
        raise ValidationError(f"FASTA parsing error: {e}")

    # Validate and create sequences
    created_sequences = []

    for fasta_seq in fasta_sequences:
        # Validate sequence and determine type
        try:
            detected_type = validate_fasta_sequence(fasta_seq, sequence_type)
        except ValidationError as e:
            raise ValidationError(f"Sequence '{fasta_seq.header}': {e}")

        # Create sequence in database
        db_sequence = Sequence(
            name=fasta_seq.header,
            sequence_data=fasta_seq.sequence_data,
            sequence_type=detected_type,
            description=fasta_seq.description,
            project_id=project_id,
            user_id=user_id,
        )
        db_session.add(db_sequence)
        await db_session.flush()

        created_sequences.append(SequenceOutput.model_validate(db_sequence))

    return FastaUploadOutput(
        sequences_created=len(created_sequences), sequences=created_sequences
    )
