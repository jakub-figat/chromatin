from dataclasses import dataclass

from core.exceptions import ValidationError


@dataclass
class FastaSequence:
    """Parsed FASTA sequence with header and data"""

    header: str
    sequence_data: str
    description: str | None = None


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
