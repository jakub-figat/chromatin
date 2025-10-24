# Average molecular weights of amino acids in Daltons (Da)
AMINO_ACID_WEIGHTS = {
    "A": 89.09,  # Alanine
    "R": 174.20,  # Arginine
    "N": 132.12,  # Asparagine
    "D": 133.10,  # Aspartic acid
    "C": 121.15,  # Cysteine
    "E": 147.13,  # Glutamic acid
    "Q": 146.15,  # Glutamine
    "G": 75.07,  # Glycine
    "H": 155.16,  # Histidine
    "I": 131.17,  # Isoleucine
    "L": 131.17,  # Leucine
    "K": 146.19,  # Lysine
    "M": 149.21,  # Methionine
    "F": 165.19,  # Phenylalanine
    "P": 115.13,  # Proline
    "S": 105.09,  # Serine
    "T": 119.12,  # Threonine
    "W": 204.23,  # Tryptophan
    "Y": 181.19,  # Tyrosine
    "V": 117.15,  # Valine
}

# Valid characters for each sequence type
DNA_CHARS = set("ACGT")
RNA_CHARS = set("ACGU")
PROTEIN_CHARS = set("ACDEFGHIKLMNPQRSTVWY")
