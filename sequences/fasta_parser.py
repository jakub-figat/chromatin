from dataclasses import dataclass
from io import StringIO

from sequences.enums import SequenceType
from sequences.consts import DNA_CHARS, RNA_CHARS, PROTEIN_CHARS
from core.exceptions import ValidationError


@dataclass
class FastaSequence:
    """Parsed FASTA sequence with header and data"""

    header: str
    sequence_data: str
    description: str | None = None


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


def parse_fasta(file_content: str) -> list[FastaSequence]:
    """
    Parse FASTA file content and return list of sequences.

    Args:
        file_content: String content of FASTA file

    Returns:
        List of FastaSequence objects

    Raises:
        ValidationError: If FASTA format is invalid or empty
    """
    sequences = []
    current_header = None
    current_description = None
    current_sequence_lines = []

    lines = file_content.strip().split("\n")

    if not lines or not any(line.strip() for line in lines):
        raise ValidationError("FASTA file is empty")

    for line_num, line in enumerate(lines, start=1):
        line = line.strip()

        if not line:
            # Skip empty lines
            continue

        if line.startswith(">"):
            # Save previous sequence if exists
            if current_header is not None:
                if not current_sequence_lines:
                    raise ValidationError(
                        f"Sequence '{current_header}' has no sequence data"
                    )

                sequences.append(
                    FastaSequence(
                        header=current_header,
                        sequence_data="".join(current_sequence_lines),
                        description=current_description,
                    )
                )

            # Parse new header
            header_line = line[1:].strip()
            if not header_line:
                raise ValidationError(f"Line {line_num}: Header is empty after '>'")

            # Split header into name and description (at first space)
            parts = header_line.split(maxsplit=1)
            current_header = parts[0]
            current_description = parts[1] if len(parts) > 1 else None
            current_sequence_lines = []

        else:
            # Sequence data line
            if current_header is None:
                raise ValidationError(
                    f"Line {line_num}: Sequence data found before header"
                )

            # Remove whitespace and validate it contains only allowed characters
            sequence_line = "".join(line.split())
            if not sequence_line:
                continue

            current_sequence_lines.append(sequence_line)

    # Save last sequence
    if current_header is not None:
        if not current_sequence_lines:
            raise ValidationError(f"Sequence '{current_header}' has no sequence data")

        sequences.append(
            FastaSequence(
                header=current_header,
                sequence_data="".join(current_sequence_lines),
                description=current_description,
            )
        )

    if not sequences:
        raise ValidationError("No valid sequences found in FASTA file")

    return sequences


def validate_fasta_sequence(
    fasta_seq: FastaSequence, expected_type: SequenceType | None = None
) -> SequenceType:
    """
    Validate a parsed FASTA sequence.

    Args:
        fasta_seq: Parsed FASTA sequence
        expected_type: If provided, validate against this type. Otherwise auto-detect.

    Returns:
        The sequence type (detected or validated)

    Raises:
        ValidationError: If sequence is invalid
    """
    if not fasta_seq.sequence_data:
        raise ValidationError(f"Sequence '{fasta_seq.header}' is empty")

    if expected_type:
        # Validate against expected type
        sequence_upper = fasta_seq.sequence_data.upper()
        sequence_set = set(sequence_upper)

        valid_chars = {
            SequenceType.DNA: DNA_CHARS,
            SequenceType.RNA: RNA_CHARS,
            SequenceType.PROTEIN: PROTEIN_CHARS,
        }[expected_type]

        if not sequence_set.issubset(valid_chars):
            invalid_chars = sequence_set - valid_chars
            raise ValidationError(
                f"Sequence '{fasta_seq.header}' contains invalid characters "
                f"for {expected_type.value}: {', '.join(sorted(invalid_chars))}"
            )

        return expected_type
    else:
        # Auto-detect type
        return detect_sequence_type(fasta_seq.sequence_data)
