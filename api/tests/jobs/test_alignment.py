"""Tests for pairwise alignment functionality"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import User
from core.exceptions import NotFoundError, ValidationError
from jobs.enums import AlignmentType
from jobs.schemas import PairwiseAlignmentParams
from jobs.tasks import (
    _generate_cigar,
    _calculate_alignment_stats,
    process_pairwise_alignment,
)
from projects import Project
from sequences import Sequence
from sequences.enums import SequenceType


# Test helper functions


def test_generate_cigar_all_matches():
    """Test CIGAR generation with all matches"""
    aligned_seq1 = "ATGC"
    aligned_seq2 = "ATGC"

    cigar = _generate_cigar(aligned_seq1, aligned_seq2)

    assert cigar == "4M"


def test_generate_cigar_with_insertions():
    """Test CIGAR generation with insertions"""
    aligned_seq1 = "ATGC"
    aligned_seq2 = "A--C"

    cigar = _generate_cigar(aligned_seq1, aligned_seq2)

    assert cigar == "1M2I1M"


def test_generate_cigar_with_deletions():
    """Test CIGAR generation with deletions"""
    aligned_seq1 = "A--C"
    aligned_seq2 = "ATGC"

    cigar = _generate_cigar(aligned_seq1, aligned_seq2)

    assert cigar == "1M2D1M"


def test_generate_cigar_complex():
    """Test CIGAR generation with mixed operations"""
    aligned_seq1 = "ATGC--ATGC"
    aligned_seq2 = "AT--GGATGC"

    cigar = _generate_cigar(aligned_seq1, aligned_seq2)

    assert cigar == "2M2I2D4M"


def test_calculate_alignment_stats_perfect_match():
    """Test stats calculation for perfect match"""
    aligned_seq1 = "ATGC"
    aligned_seq2 = "ATGC"

    stats = _calculate_alignment_stats(aligned_seq1, aligned_seq2)

    assert stats["alignment_length"] == 4
    assert stats["matches"] == 4
    assert stats["mismatches"] == 0
    assert stats["gaps"] == 0
    assert stats["identity_percent"] == 100.0


def test_calculate_alignment_stats_with_mismatches():
    """Test stats calculation with mismatches"""
    aligned_seq1 = "ATGC"
    aligned_seq2 = "ATAT"

    stats = _calculate_alignment_stats(aligned_seq1, aligned_seq2)

    assert stats["alignment_length"] == 4
    assert stats["matches"] == 2  # A and T match
    assert stats["mismatches"] == 2  # G->A, C->T
    assert stats["gaps"] == 0
    assert stats["identity_percent"] == 50.0


def test_calculate_alignment_stats_with_gaps():
    """Test stats calculation with gaps"""
    aligned_seq1 = "ATGC--"
    aligned_seq2 = "AT--GC"

    stats = _calculate_alignment_stats(aligned_seq1, aligned_seq2)

    assert stats["alignment_length"] == 6
    assert stats["matches"] == 2  # A and C match
    assert stats["mismatches"] == 0
    assert stats["gaps"] == 4
    assert stats["identity_percent"] == 100.0  # 2 matches / 2 non-gap positions


# Test main alignment function


@pytest.fixture
async def test_sequences(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Create test sequences for alignment"""
    seq1 = Sequence(
        name="seq1",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCATGCATGC",
        length=12,
        gc_content=0.5,
        molecular_weight=None,
        description="Test sequence 1",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    seq2 = Sequence(
        name="seq2",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCATGC",
        length=8,
        gc_content=0.5,
        molecular_weight=None,
        description="Test sequence 2",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    test_session.add(seq1)
    test_session.add(seq2)
    await test_session.flush()
    await test_session.refresh(seq1)
    await test_session.refresh(seq2)

    return seq1, seq2


async def test_process_global_alignment(test_session: AsyncSession, test_sequences):
    """Test global alignment (Needleman-Wunsch)"""
    seq1, seq2 = test_sequences

    params = PairwiseAlignmentParams(
        job_type="PAIRWISE_ALIGNMENT",
        sequence_id_1=seq1.id,
        sequence_id_2=seq2.id,
        alignment_type=AlignmentType.GLOBAL,
        match_score=2,
        mismatch_score=-1,
        gap_open_score=-5,
        gap_extend_score=-1,
    )

    result = await process_pairwise_alignment(params, test_session)

    # Verify result structure
    assert result["sequence_id_1"] == seq1.id
    assert result["sequence_id_2"] == seq2.id
    assert result["sequence_name_1"] == "seq1"
    assert result["sequence_name_2"] == "seq2"
    assert result["alignment_type"] == "GLOBAL"
    assert isinstance(result["alignment_score"], float)
    assert isinstance(result["aligned_seq_1"], str)
    assert isinstance(result["aligned_seq_2"], str)
    assert isinstance(result["alignment_length"], int)
    assert isinstance(result["matches"], int)
    assert isinstance(result["mismatches"], int)
    assert isinstance(result["gaps"], int)
    assert isinstance(result["identity_percent"], float)
    assert isinstance(result["cigar"], str)
    assert result["scoring_params"]["match_score"] == 2
    assert result["scoring_params"]["mismatch_score"] == -1

    # Verify alignment makes sense
    assert result["alignment_length"] >= max(
        len(seq1.sequence_data), len(seq2.sequence_data)
    )
    assert result["matches"] > 0  # Should have some matches
    assert 0 <= result["identity_percent"] <= 100


async def test_process_local_alignment(test_session: AsyncSession, test_sequences):
    """Test local alignment (Smith-Waterman)"""
    seq1, seq2 = test_sequences

    params = PairwiseAlignmentParams(
        job_type="PAIRWISE_ALIGNMENT",
        sequence_id_1=seq1.id,
        sequence_id_2=seq2.id,
        alignment_type=AlignmentType.LOCAL,
        match_score=2,
        mismatch_score=-1,
        gap_open_score=-5,
        gap_extend_score=-1,
    )

    result = await process_pairwise_alignment(params, test_session)

    # Verify result structure
    assert result["alignment_type"] == "LOCAL"
    assert isinstance(result["alignment_score"], float)

    # Local alignment should find best matching region
    assert result["alignment_length"] > 0
    assert result["matches"] > 0


async def test_alignment_with_default_params(
    test_session: AsyncSession, test_sequences
):
    """Test alignment with default scoring parameters"""
    seq1, seq2 = test_sequences

    params = PairwiseAlignmentParams(
        job_type="PAIRWISE_ALIGNMENT",
        sequence_id_1=seq1.id,
        sequence_id_2=seq2.id,
        # alignment_type defaults to GLOBAL
        # scoring params use defaults
    )

    result = await process_pairwise_alignment(params, test_session)

    assert result["alignment_type"] == "GLOBAL"
    assert result["scoring_params"]["match_score"] == 2
    assert result["scoring_params"]["mismatch_score"] == -1
    assert result["scoring_params"]["gap_open_score"] == -5
    assert result["scoring_params"]["gap_extend_score"] == -1


async def test_alignment_nonexistent_sequence(
    test_session: AsyncSession, test_sequences
):
    """Test alignment with non-existent sequence raises NotFoundError"""
    seq1, _ = test_sequences

    params = PairwiseAlignmentParams(
        job_type="PAIRWISE_ALIGNMENT",
        sequence_id_1=seq1.id,
        sequence_id_2=99999,  # Non-existent
    )

    with pytest.raises(NotFoundError):
        await process_pairwise_alignment(params, test_session)


async def test_alignment_different_sequence_types(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Test alignment with different sequence types raises ValidationError"""
    # Create DNA sequence
    dna_seq = Sequence(
        name="dna_seq",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCATGC",
        length=8,
        gc_content=0.5,
        molecular_weight=None,
        description="DNA sequence",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    # Create protein sequence
    protein_seq = Sequence(
        name="protein_seq",
        sequence_type=SequenceType.PROTEIN,
        sequence_data="MVHLTPEEK",
        length=9,
        gc_content=None,
        molecular_weight=1000.0,
        description="Protein sequence",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    test_session.add(dna_seq)
    test_session.add(protein_seq)
    await test_session.flush()
    await test_session.refresh(dna_seq)
    await test_session.refresh(protein_seq)

    params = PairwiseAlignmentParams(
        job_type="PAIRWISE_ALIGNMENT",
        sequence_id_1=dna_seq.id,
        sequence_id_2=protein_seq.id,
    )

    with pytest.raises(ValidationError) as exc_info:
        await process_pairwise_alignment(params, test_session)

    assert "different types" in str(exc_info.value).lower()


async def test_alignment_protein_sequences(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Test alignment works with protein sequences"""
    # Create two protein sequences
    protein_seq1 = Sequence(
        name="protein1",
        sequence_type=SequenceType.PROTEIN,
        sequence_data="MVHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQRF",
        length=43,
        gc_content=None,
        molecular_weight=None,
        description="Hemoglobin alpha chain fragment",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    protein_seq2 = Sequence(
        name="protein2",
        sequence_type=SequenceType.PROTEIN,
        sequence_data="MVHLTPEEKSAVTALWGKVNV",
        length=21,
        gc_content=None,
        molecular_weight=None,
        description="Shorter protein",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    test_session.add(protein_seq1)
    test_session.add(protein_seq2)
    await test_session.flush()
    await test_session.refresh(protein_seq1)
    await test_session.refresh(protein_seq2)

    params = PairwiseAlignmentParams(
        job_type="PAIRWISE_ALIGNMENT",
        sequence_id_1=protein_seq1.id,
        sequence_id_2=protein_seq2.id,
        alignment_type=AlignmentType.LOCAL,
    )

    result = await process_pairwise_alignment(params, test_session)

    # Should successfully align proteins
    assert result["alignment_score"] > 0
    assert result["matches"] > 0
    assert (
        result["identity_percent"] > 85
    )  # These sequences are very similar (86% identity)


async def test_alignment_identical_sequences(
    test_session: AsyncSession, test_user: User, test_project: Project
):
    """Test alignment of identical sequences"""
    seq1 = Sequence(
        name="identical1",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCATGC",
        length=8,
        gc_content=0.5,
        molecular_weight=None,
        description="Sequence 1",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    seq2 = Sequence(
        name="identical2",
        sequence_type=SequenceType.DNA,
        sequence_data="ATGCATGC",
        length=8,
        gc_content=0.5,
        molecular_weight=None,
        description="Sequence 2",
        user_id=test_user.id,
        project_id=test_project.id,
    )

    test_session.add(seq1)
    test_session.add(seq2)
    await test_session.flush()
    await test_session.refresh(seq1)
    await test_session.refresh(seq2)

    params = PairwiseAlignmentParams(
        job_type="PAIRWISE_ALIGNMENT",
        sequence_id_1=seq1.id,
        sequence_id_2=seq2.id,
    )

    result = await process_pairwise_alignment(params, test_session)

    # Identical sequences should have perfect alignment
    assert result["identity_percent"] == 100.0
    assert result["gaps"] == 0
    assert result["mismatches"] == 0
    assert result["matches"] == 8
    assert result["cigar"] == "8M"
