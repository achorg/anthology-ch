"""Text and string utility functions for the anthology journal processor."""

import re
import unicodedata


def slugify(text: str, max_width: int) -> str:
    """
    Convert text to a lowercase, dash-separated slug.

    The slug contains only [a-z0-9] characters, with diacritics removed
    and punctuation converted to spaces. Consecutive spaces collapse to
    one dash. The result is truncated by words to not exceed max_width
    (no partial words).

    Common words like 'and', 'the', 'an', 'a' are removed from the slug.

    Args:
        text: The text to convert to a slug
        max_width: Maximum width of the slug (truncates at word boundaries)

    Returns:
        A slugified string suitable for URLs and filenames

    Raises:
        TypeError: If max_width is not an integer

    Examples:
        >>> slugify("Hello World", 20)
        'hello-world'
        >>> slugify("Café & Bar", 20)
        'cafe-bar'
        >>> slugify("The Quick Brown Fox", 10)
        'quick-brown'
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    if not isinstance(max_width, int):
        raise TypeError("max_width must be an int")
    if max_width <= 0:
        return ""

    # 1) Remove diacritics (é -> e), normalize width/compatibility
    normalized = unicodedata.normalize("NFKD", text)
    no_diacritics = "".join(ch for ch in normalized if not unicodedata.combining(ch))

    # 2) Lowercase, turn any non-alphanumeric into spaces
    lowered = no_diacritics.lower()
    # Keep only ASCII a-z and digits; treat everything else as space
    lowered = re.sub(r"[^0-9a-z]+", " ", lowered)

    # Remove common words
    lowered = lowered.replace(" and ", " ")
    lowered = lowered.replace(" the ", " ")
    lowered = lowered.replace(" an ", " ")
    lowered = lowered.replace(" a ", " ")

    # 3) Split to words (collapses multiple spaces), then pack without exceeding max_width
    words = lowered.split()
    slug_parts = []
    current_len = 0

    for w in words:
        # (w already matches [a-z0-9]+ by construction)
        if not w:
            continue
        proposed_len = current_len + (1 if slug_parts else 0) + len(w)
        if proposed_len > max_width:
            # Skip this word entirely (do not truncate)
            continue
        slug_parts.append(w)
        current_len = proposed_len

    # 4) Join with single dashes (no leading/trailing/multiple dashes by construction)
    return "-".join(slug_parts)


def convert_latex_to_unicode(text: str) -> str:
    """
    Convert LaTeX special characters to Unicode equivalents.

    Currently handles:
    - Triple dash (---) to em dash (—)

    Args:
        text: Text potentially containing LaTeX markup

    Returns:
        Text with LaTeX converted to Unicode
    """
    text = text.replace("---", "—")
    return text


def strip_html_tags(text: str) -> str:
    """
    Remove all HTML tags from a string, keeping only text content.

    Also cleans up multiple spaces and newlines, collapsing them to
    single spaces.

    Args:
        text: String potentially containing HTML tags

    Returns:
        Plain text with all HTML tags removed

    Examples:
        >>> strip_html_tags('<p>Hello <strong>world</strong></p>')
        'Hello world'
        >>> strip_html_tags('Plain text')
        'Plain text'
    """
    # Remove HTML tags using regex
    clean = re.sub(r"<[^>]+>", "", text)
    # Clean up multiple spaces and newlines
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()
