import pytest

from sequences.fasta_parser import (
    parse_fasta,
    FastaSequence,
)
from sequences.enums import SequenceType
from core.exceptions import ValidationError


# Tests for parse_fasta function


def test_parse_single_sequence():
    """Test parsing a single sequence"""
    fasta_content = ">seq1 test sequence\nACGT"
    sequences = parse_fasta(fasta_content)

    assert len(sequences) == 1
    assert sequences[0].header == "seq1"
    assert sequences[0].sequence_data == "ACGT"
    assert sequences[0].description == "test sequence"


def test_parse_multiple_sequences():
    """Test parsing multiple sequences"""
    fasta_content = """
>seq1 description1
ACGT
TGCA
>seq2 description2
GGGG
CCCC
    """.strip()

    sequences = parse_fasta(fasta_content)

    assert len(sequences) == 2
    assert sequences[0].header == "seq1"
    assert sequences[0].sequence_data == "ACGTTGCA"
    assert sequences[0].description == "description1"
    assert sequences[1].header == "seq2"
    assert sequences[1].sequence_data == "GGGGCCCC"
    assert sequences[1].description == "description2"


def test_parse_sequence_without_description():
    """Test parsing sequence with no description"""
    fasta_content = ">seq1\nACGT"
    sequences = parse_fasta(fasta_content)

    assert len(sequences) == 1
    assert sequences[0].header == "seq1"
    assert sequences[0].description is None


def test_parse_sequence_with_whitespace():
    """Test parsing removes whitespace from sequence data"""
    fasta_content = ">seq1\nAC GT\nTG CA"
    sequences = parse_fasta(fasta_content)

    assert sequences[0].sequence_data == "ACGTTGCA"


@pytest.mark.parametrize(
    "fasta_content,error_match",
    [
        ("", "FASTA file is empty"),
        ("   \n\n  \n", "FASTA file is empty"),
        ("ACGT", "Sequence data found before header"),
        (">\nACGT", "Header is empty after '>'"),
        (">seq1", "has no sequence data"),
    ],
)
def test_parse_invalid_fasta(fasta_content, error_match):
    """Test parsing invalid FASTA content raises appropriate errors"""
    with pytest.raises(ValidationError, match=error_match):
        parse_fasta(fasta_content)


def test_parse_sequence_with_empty_lines():
    """Test parsing handles empty lines correctly"""
    fasta_content = """
>seq1

ACGT

TGCA

>seq2
GGGG
    """
    sequences = parse_fasta(fasta_content)

    assert len(sequences) == 2
    assert sequences[0].sequence_data == "ACGTTGCA"
    assert sequences[1].sequence_data == "GGGG"


# Tests with realistic FASTA examples


def test_parse_protein_fasta():
    """Test parsing a realistic protein FASTA"""
    fasta_content = """
>sp|P12345|EXAMPLE_HUMAN Example protein OS=Homo sapiens
MKLLIVLLVALVALAASNAKIDQLSSDVQTLNAKVDQLSSDVQTLNAKVDQLSSDVQT
LNAKVDQLSSDVQTLNAKVDQLSSDVQTLNAKVDQLSSDVQTLNAKVDQLSSDVQTL
    """
    sequences = parse_fasta(fasta_content)

    assert len(sequences) == 1
    assert sequences[0].header == "sp|P12345|EXAMPLE_HUMAN"
    assert sequences[0].description == "Example protein OS=Homo sapiens"
    assert len(sequences[0].sequence_data) > 100


def test_parse_multi_sequence_genome():
    """Test parsing multiple chromosome sequences"""
    fasta_content = """
>chr1 chromosome 1
ATCGATCGATCG
>chr2 chromosome 2
GCTAGCTAGCTA
>chrX chromosome X
TTAATTAATTAA
    """
    sequences = parse_fasta(fasta_content)

    assert len(sequences) == 3
    assert sequences[0].header == "chr1"
    assert sequences[1].header == "chr2"
    assert sequences[2].header == "chrX"
