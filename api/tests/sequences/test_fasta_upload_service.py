"""Test FASTA upload service functionality including file storage"""

import pytest
from io import BytesIO
from pathlib import Path
import hashlib

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import User
from core.consts import MEGABYTE
from core.exceptions import ValidationError
from core.storage import get_storage_service
from core.config import settings
from projects import Project
from sequences import Sequence
from sequences.enums import SequenceType
from sequences.service import upload_fasta


async def test_upload_fasta_single_file_small_sequences(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Test uploading single FASTA file with small sequences (stored in DB)"""
    fasta_content = b">seq_small_1\nATGC\n>seq_small_2\nGGCC"
    file = UploadFile(filename="test.fasta", file=BytesIO(fasta_content))

    result = await upload_fasta(
        [file], test_project.id, test_user.id, test_session, None
    )

    assert result.sequences_created == 2

    # Verify sequences in database
    stmt = select(Sequence).where(Sequence.project_id == test_project.id)
    sequences = list(await test_session.scalars(stmt))

    assert len(sequences) == 2
    assert sequences[0].name == "seq_small_1"
    assert sequences[0].sequence_data == "ATGC"
    assert sequences[0].file_path is None  # Small sequence, stored in DB
    assert sequences[0].length == 4

    assert sequences[1].name == "seq_small_2"
    assert sequences[1].sequence_data == "GGCC"
    assert sequences[1].file_path is None
    assert sequences[1].length == 4


async def test_upload_fasta_large_sequence_uses_file_storage(
    test_session: AsyncSession, test_user: User, test_project: Project, cleanup_storage
):
    """Test uploading large sequence (>10KB) uses file storage"""
    # Create sequence larger than threshold (10KB)
    large_sequence = "A" * 15000  # 15KB
    fasta_content = f">large_seq\n{large_sequence}".encode()
    file = UploadFile(filename="large.fasta", file=BytesIO(fasta_content))

    result = await upload_fasta(
        [file], test_project.id, test_user.id, test_session, None
    )

    assert result.sequences_created == 1

    # Verify sequence uses file storage
    stmt = select(Sequence).where(Sequence.project_id == test_project.id)
    sequences = list(await test_session.scalars(stmt))

    assert len(sequences) == 1
    assert sequences[0].name == "large_seq"
    assert sequences[0].sequence_data is None  # Not stored in DB
    assert sequences[0].file_path is not None  # Stored in file
    assert sequences[0].length == 15000

    # Verify file actually exists and contains correct data
    storage = get_storage_service()
    file_content = await storage.read(sequences[0].file_path)
    assert file_content == large_sequence

    # Verify file exists on filesystem
    file_path = Path(settings.LOCAL_STORAGE_PATH) / sequences[0].file_path
    assert file_path.exists()

    # Register for cleanup
    cleanup_storage(sequences[0].file_path)


async def test_upload_fasta_multiple_files(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Test uploading multiple FASTA files"""
    file1 = UploadFile(filename="file1.fasta", file=BytesIO(b">seq_multi_1\nATGC"))
    file2 = UploadFile(
        filename="file2.fasta", file=BytesIO(b">seq_multi_2\nGGCC\n>seq_multi_3\nTTAA")
    )

    result = await upload_fasta(
        [file1, file2], test_project.id, test_user.id, test_session, None
    )

    assert result.sequences_created == 3

    # Verify all sequences in database
    stmt = (
        select(Sequence)
        .where(Sequence.project_id == test_project.id)
        .order_by(Sequence.id)
    )
    sequences = list(await test_session.scalars(stmt))

    assert len(sequences) == 3
    assert [s.name for s in sequences] == ["seq_multi_1", "seq_multi_2", "seq_multi_3"]


# TODO: ON CONFLICT (user_id, name) DO UPDATE
# async def test_upload_fasta_deterministic_filenames(
#     test_session: AsyncSession, test_user: User, test_project: Project, cleanup_storage
# ):
#     """Test that same sequence content gets same filename (idempotency)"""
#     # Create large sequence
#     large_sequence = "G" * 15000
#     fasta_content1 = f">seq_deterministic_1\n{large_sequence}".encode()
#     fasta_content2 = f">seq_deterministic_1\n{large_sequence}".encode()
#
#     # Upload twice with different names but same content
#     file1 = UploadFile(filename="test1.fasta", file=BytesIO(fasta_content1))
#     await upload_fasta([file1], test_project.id, test_user.id, test_session, None)
#
#     file2 = UploadFile(filename="test2.fasta", file=BytesIO(fasta_content2))
#     await upload_fasta([file2], test_project.id, test_user.id, test_session, None)
#
#     # Verify both use same file path (deterministic)
#     stmt = select(Sequence).where(Sequence.project_id == test_project.id)
#     sequences = list(await test_session.scalars(stmt))
#
#     assert len(sequences) == 2
#     assert sequences[0].file_path == sequences[1].file_path  # Same hash!
#
#     # Verify filename matches content hash
#     expected_hash = hashlib.sha256(large_sequence.encode()).hexdigest()
#     assert sequences[0].file_path == f"{expected_hash}.txt"
#
#     # Register for cleanup
#     if sequences[0].file_path:
#         cleanup_storage(sequences[0].file_path)


async def test_upload_fasta_cleanup_on_failure(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Test that storage files are cleaned up when transaction fails"""
    # Create large sequence
    large_sequence = "C" * 15000
    # Invalid FASTA - second sequence has invalid characters for DNA
    fasta_content = f">seq1\n{large_sequence}\n>seq2\nXYZ123".encode()
    file = UploadFile(filename="invalid.fasta", file=BytesIO(fasta_content))

    # Calculate expected file path for first sequence
    expected_hash = hashlib.sha256(large_sequence.encode()).hexdigest()
    expected_file_path = Path(settings.LOCAL_STORAGE_PATH) / f"{expected_hash}.txt"

    # Should fail validation on second sequence
    with pytest.raises(ValidationError):
        await upload_fasta(
            [file], test_project.id, test_user.id, test_session, SequenceType.DNA
        )

    # Verify file was cleaned up from filesystem
    assert not expected_file_path.exists(), (
        "File should have been cleaned up after failed transaction"
    )


async def test_upload_fasta_file_size_limit_exceeded(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Test that exceeding file size limit fails"""
    # Create file larger than limit
    huge_sequence = "A" * (settings.MAX_FASTA_FILE_SIZE + 1000)
    fasta_content = f">huge\n{huge_sequence}".encode()
    file = UploadFile(filename="huge.fasta", file=BytesIO(fasta_content))

    with pytest.raises(ValidationError, match="too large"):
        await upload_fasta([file], test_project.id, test_user.id, test_session, None)


# TODO: mock file sizes
# async def test_upload_fasta_total_size_limit_exceeded(
#     test_session: AsyncSession, test_user: User, test_project: Project
# ):
#     """Test that exceeding total upload size limit fails"""
#     # Create multiple files that together exceed total limit
#     file_size = settings.MAX_FASTA_FILE_SIZE // 2 - MEGABYTE
#     sequence = "A" * file_size
#
#     file1 = UploadFile(filename="file1.fasta", file=BytesIO(f">seq1\n{sequence}".encode()))
#     file2 = UploadFile(filename="file2.fasta", file=BytesIO(f">seq2\n{sequence}".encode()))
#
#     with pytest.raises(ValidationError, match="Total upload size"):
#         await upload_fasta([file1, file2], test_project.id, test_user.id, test_session, None)


async def test_upload_fasta_mixed_storage_strategies(
    test_session: AsyncSession, test_user: User, test_project: Project, cleanup_storage
):
    """Test upload with both small (DB) and large (file) sequences"""
    small_seq = "ATGC"
    large_seq = "G" * 15000
    fasta_content = f">small\n{small_seq}\n>large\n{large_seq}".encode()
    file = UploadFile(filename="mixed.fasta", file=BytesIO(fasta_content))

    result = await upload_fasta(
        [file], test_project.id, test_user.id, test_session, None
    )

    assert result.sequences_created == 2

    # Verify sequences
    stmt = (
        select(Sequence)
        .where(Sequence.project_id == test_project.id)
        .order_by(Sequence.id)
    )
    sequences = list(await test_session.scalars(stmt))

    # Small sequence in DB
    assert sequences[0].name == "small"
    assert sequences[0].sequence_data == small_seq
    assert sequences[0].file_path is None

    # Large sequence in file
    assert sequences[1].name == "large"
    assert sequences[1].sequence_data is None
    assert sequences[1].file_path is not None

    # Verify file exists
    storage = get_storage_service()
    file_content = await storage.read(sequences[1].file_path)
    assert file_content == large_seq

    # Register for cleanup
    cleanup_storage(sequences[1].file_path)
