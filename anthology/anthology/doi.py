"""DOI (Digital Object Identifier) operations for the anthology journal processor."""

import random
import re
import string

# Default DOI prefix for the anthology
DOI_PREFIX = "10.63744"

# Length of the random suffix for generated DOIs
DOI_SUFFIX_LENGTH = 12


def is_doi_placeholder(doi: str) -> bool:
    """
    Check if a DOI is a placeholder that needs to be replaced.

    Placeholder DOIs include:
    - Empty or whitespace-only strings
    - Common placeholder patterns like '00000/00000', '0', 'XXXXX'
    - Strings containing only zeros, slashes, and @ signs

    Args:
        doi: The DOI string to check

    Returns:
        True if the DOI is a placeholder, False otherwise

    Examples:
        >>> is_doi_placeholder('')
        True
        >>> is_doi_placeholder('00000/00000')
        True
        >>> is_doi_placeholder('10.1234/abcd')
        False
    """
    if not doi or not doi.strip():
        return True

    if doi.strip() in ["00000/00000", "0", "00000", "XXXXX"]:
        return True

    if re.match(r"^[0/@]+$", doi.strip()):
        return True

    return False


def generate_doi(
    prefix: str = DOI_PREFIX, suffix_length: int = DOI_SUFFIX_LENGTH
) -> str:
    """
    Generate a new DOI with the given prefix and random suffix.

    The suffix consists of a random letter (excluding O and l to avoid confusion)
    followed by random alphanumeric characters.

    Args:
        prefix: The DOI prefix (default: DOI_PREFIX constant)
        suffix_length: Length of the random suffix (default: DOI_SUFFIX_LENGTH constant)

    Returns:
        A new DOI string in the format "prefix/suffix"

    Examples:
        >>> doi = generate_doi("10.63744", 12)
        >>> len(doi.split('/')[-1])
        12
        >>> doi.startswith("10.63744/")
        True
    """
    # Exclude O and l to avoid confusion with 0 and 1
    letters = "".join(c for c in string.ascii_letters if c not in "Ol")
    numbers = string.digits

    # Start with a letter
    suffix = random.choice(letters)

    # Add remaining characters
    allowed_chars = letters + numbers
    suffix += "".join(random.choices(allowed_chars, k=suffix_length - 1))

    return f"{prefix}/{suffix}"
