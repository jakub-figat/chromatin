import itertools

from core.exceptions import ValidationError
from sequences.consts import DNA_CHARS, RNA_CHARS, PROTEIN_CHARS
from sequences.enums import SequenceType


RNA_CODON_TABLE = {
    "UUU": "F",
    "UUC": "F",
    "UUA": "L",
    "UUG": "L",
    "CUU": "L",
    "CUC": "L",
    "CUA": "L",
    "CUG": "L",
    "AUU": "I",
    "AUC": "I",
    "AUA": "I",
    "AUG": "M",
    "GUU": "V",
    "GUC": "V",
    "GUA": "V",
    "GUG": "V",
    "UCU": "S",
    "UCC": "S",
    "UCA": "S",
    "UCG": "S",
    "CCU": "P",
    "CCC": "P",
    "CCA": "P",
    "CCG": "P",
    "ACU": "T",
    "ACC": "T",
    "ACA": "T",
    "ACG": "T",
    "GCU": "A",
    "GCC": "A",
    "GCA": "A",
    "GCG": "A",
    "UAU": "Y",
    "UAC": "Y",
    "UAA": "*",
    "UAG": "*",  # Stop codons
    "CAU": "H",
    "CAC": "H",
    "CAA": "Q",
    "CAG": "Q",
    "AAU": "N",
    "AAC": "N",
    "AAA": "K",
    "AAG": "K",
    "GAU": "D",
    "GAC": "D",
    "GAA": "E",
    "GAG": "E",
    "UGU": "C",
    "UGC": "C",
    "UGA": "*",  # Stop codon
    "UGG": "W",
    "CGU": "R",
    "CGC": "R",
    "CGA": "R",
    "CGG": "R",
    "AGU": "S",
    "AGC": "S",
    "AGA": "R",
    "AGG": "R",
    "GGU": "G",
    "GGC": "G",
    "GGA": "G",
    "GGG": "G",
}


def detect_sequence_type(sequence_data: str) -> SequenceType:
    """
    Auto-detect sequence type based on characters present.

    Raises ValidationError if sequence contains invalid characters.
    """
    sequence_upper = sequence_data.upper()
    sequence_set = set(sequence_upper)

    # Check if it's DNA (ACGT only)
    if sequence_set.issubset(DNA_CHARS):
        return SequenceType.DNA

    # Check if it's RNA (ACGU only)
    if sequence_set.issubset(RNA_CHARS):
        return SequenceType.RNA

    # Check if it's protein
    if sequence_set.issubset(PROTEIN_CHARS):
        return SequenceType.PROTEIN

    # Invalid characters found
    invalid_chars = sequence_set - (DNA_CHARS | RNA_CHARS | PROTEIN_CHARS)
    raise ValidationError(
        f"Sequence contains invalid characters: {', '.join(sorted(invalid_chars))}"
    )


def validate_sequence_data(
    sequence_data: str,
    sequence_name: str | None = None,
    expected_type: SequenceType | None = None,
) -> SequenceType:
    name = sequence_name or ""
    """
    Validate a sequence.

    Args:
        sequence_data: Sequence data
        expected_type: If provided, validate against this type. Otherwise auto-detect.

    Returns:
        The sequence type (detected or validated)

    Raises:
        ValidationError: If sequence is invalid
    """
    if not sequence_data:
        raise ValidationError(f"Sequence '{name}' is empty")

    if expected_type:
        # Validate against expected type
        sequence_upper = sequence_data.upper()
        sequence_set = set(sequence_upper)

        valid_chars = {
            SequenceType.DNA: DNA_CHARS,
            SequenceType.RNA: RNA_CHARS,
            SequenceType.PROTEIN: PROTEIN_CHARS,
        }[expected_type]

        if not sequence_set.issubset(valid_chars):
            invalid_chars = sequence_set - valid_chars
            raise ValidationError(
                f"Sequence '{name}' contains invalid characters "
                f"for {expected_type.value}: {', '.join(sorted(invalid_chars))}"
            )

        return expected_type
    else:
        return detect_sequence_type(sequence_data)


def get_dna_reverse_complement(sequence_data: str) -> str:
    reverse_complement = {
        "A": "T",
        "C": "G",
        "G": "C",
        "T": "A",
    }

    validate_sequence_data(sequence_data, expected_type=SequenceType.DNA)
    return "".join(reverse_complement[base] for base in sequence_data)


def get_rna_from_dna(sequence_data: str) -> str:
    validate_sequence_data(sequence_data, expected_type=SequenceType.DNA)
    return "".join([base if base != "T" else "U" for base in sequence_data])


def get_protein_from_rna(sequence_data: str) -> str:
    validate_sequence_data(sequence_data, expected_type=SequenceType.RNA)
    rna_sequence = sequence_data[: len(sequence_data) - len(sequence_data) % 3]

    protein = []
    for codon_number in range(0, len(rna_sequence) // 3):
        codon = rna_sequence[codon_number * 3 : codon_number * 3 + 3]
        amino_acid = RNA_CODON_TABLE[codon]
        if amino_acid == "*":
            break
        protein.append(amino_acid)

    return "".join(protein)


def get_protein_from_dna(sequence_data: str) -> str:
    validate_sequence_data(sequence_data, expected_type=SequenceType.DNA)
    return get_protein_from_rna(get_rna_from_dna(sequence_data))
