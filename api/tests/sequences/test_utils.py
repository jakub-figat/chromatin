import pytest

from core.exceptions import ValidationError
from sequences.enums import SequenceType
from sequences.utils import (
    get_dna_reverse_complement,
    detect_sequence_type,
    validate_sequence_data,
    get_rna_from_dna,
    get_protein_from_dna,
    get_protein_from_rna,
)


@pytest.mark.parametrize(
    "sequence_data,expected_type",
    [
        ("ACGT", SequenceType.DNA),
        ("acgt", SequenceType.DNA),
        ("AAAACCCCGGGGTTTT", SequenceType.DNA),
        ("ACGU", SequenceType.RNA),
        ("acgu", SequenceType.RNA),
        ("AAAACCCCGGGGUUUU", SequenceType.RNA),
        ("ARNDCEQGHILKMFPSTWYV", SequenceType.PROTEIN),
        ("arndceqghilkmfpstwyv", SequenceType.PROTEIN),
        ("MKLLILVLLVALVALAAS", SequenceType.PROTEIN),
        ("ACGACG", SequenceType.DNA),  # ACG is valid for both, should detect DNA
    ],
)
def test_detect_sequence_type(sequence_data, expected_type):
    """Test detection of sequence types"""
    assert detect_sequence_type(sequence_data) == expected_type


@pytest.mark.parametrize(
    "invalid_sequence",
    [
        "ACGT123",
        "ACGT-N-N",
        "ACGT*",
    ],
)
def test_detect_invalid_characters(invalid_sequence):
    """Test detection fails with invalid characters"""
    with pytest.raises(ValidationError, match="invalid characters"):
        detect_sequence_type(invalid_sequence)


# Tests for validate_sequence_data function


def test_validate_with_auto_detect():
    """Test validation with auto-detection"""
    seq_type = validate_sequence_data("ACGT")
    assert seq_type == SequenceType.DNA


def test_validate_with_expected_type_valid():
    """Test validation with expected type that matches"""
    seq_type = validate_sequence_data("ACGT", expected_type=SequenceType.DNA)
    assert seq_type == SequenceType.DNA


def test_validate_with_expected_type_invalid():
    """Test validation with expected type that doesn't match"""
    with pytest.raises(ValidationError, match="contains invalid characters for RNA"):
        validate_sequence_data("ACGT", expected_type=SequenceType.RNA)


def test_validate_empty_sequence():
    """Test validation of empty sequence raises error"""
    with pytest.raises(ValidationError, match="is empty"):
        validate_sequence_data("")


def test_validate_protein_as_dna_fails():
    """Test that protein sequences fail DNA validation"""
    with pytest.raises(ValidationError, match="contains invalid characters for DNA"):
        validate_sequence_data("MKLLILVLLVALVALAAS", expected_type=SequenceType.DNA)


def test_validate_dna_as_protein_succeeds():
    """Test that DNA sequences can validate as protein (subset)"""
    # DNA chars (ACGT) are all valid protein amino acids
    seq_type = validate_sequence_data("ACGT", expected_type=SequenceType.PROTEIN)
    assert seq_type == SequenceType.PROTEIN


@pytest.mark.parametrize(
    "sequence_data,expected_reverse_complement",
    [("ATCG", "TAGC"), ("CCGG", "GGCC"), ("ACACGCGC", "TGTGCGCG")],
)
def test_get_dna_reverse_complement(
    sequence_data: str, expected_reverse_complement: str
):
    assert get_dna_reverse_complement(sequence_data) == expected_reverse_complement


@pytest.mark.parametrize(
    "sequence_data,expected_rna_sequence",
    [("ATCG", "AUCG"), ("AAAA", "AAAA"), ("ATATATGCGCGC", "AUAUAUGCGCGC")],
)
def test_get_rna_sequence(sequence_data: str, expected_rna_sequence: str):
    assert get_rna_from_dna(sequence_data) == expected_rna_sequence


def test_transcription_and_translation():
    dna_sequence = "ATGGCCATTGTAATGGGCCGCTGAAAGGGTGCCCGATAG"
    expected_rna_sequence = "AUGGCCAUUGUAAUGGGCCGCUGAAAGGGUGCCCGAUAG"
    expected_protein_sequence = "MAIVMGR"

    rna_sequence = get_rna_from_dna(dna_sequence)

    assert get_rna_from_dna(dna_sequence) == expected_rna_sequence
    assert get_protein_from_rna(rna_sequence) == expected_protein_sequence
