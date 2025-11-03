"""BibTeX citation file generation for the anthology journal processor."""

from pathlib import Path
from typing import Union, List


def write_bibtex_article(
    title: str,
    volume: str,
    authors: Union[str, List[str]],
    year: str,
    journal: str,
    editors: Union[str, List[str]],
    pages: str,
    doi: str,
    output_path: Union[str, Path],
) -> str:
    """
    Generate and write a BibTeX entry for a journal article.

    Creates a properly formatted BibTeX @article entry with all provided
    metadata, escaping special LaTeX characters as needed.

    Args:
        title: Article title
        volume: Journal volume number
        authors: Author name(s) - can be a string or list of strings
        year: Publication year
        journal: Journal name
        editors: Editor name(s) - can be a string or list of strings
        pages: Page range (e.g., "10--20")
        doi: Digital Object Identifier
        output_path: Path where the .bib file should be written

    Returns:
        The generated BibTeX entry as a string

    Note:
        The citation key is generated from the DOI with '/' replaced by '@'.
        Special LaTeX characters in text fields are automatically escaped.
    """
    def _escape_latex(s: str) -> str:
        """Escape special LaTeX characters in a string."""
        repl = {
            "\\": r"\\",
            "{": r"\{",
            "}": r"\}",
            "%": r"\%",
            "$": r"\$",
            "&": r"\&",
            "#": r"\#",
            "_": r"\_",
            "~": r"\textasciitilde{}",
            "^": r"\textasciicircum{}",
        }
        out = []
        for ch in s:
            out.append(repl.get(ch, ch))
        return "".join(out)

    def _join_people(p: Union[str, List[str], None]) -> Union[str, None]:
        """Join a list of people names with ' and ' separator."""
        if p is None:
            return None
        if isinstance(p, str):
            return p.strip()
        return " and ".join(x.strip() for x in p if x and x.strip())

    # Normalize inputs
    authors_field = _join_people(authors)
    editors_field = _join_people(editors)

    # Build field list
    fields = [
        ("title",   _escape_latex(title)),
        ("author",  _escape_latex(authors_field) if authors_field else None),
        ("year",    str(year)),
        ("journal", _escape_latex(journal)),
        ("volume",  str(volume)),
        ("pages",   _escape_latex(pages)),
        ("editor",  _escape_latex(editors_field) if editors_field else None),
        ("doi",     str(doi)),
    ]

    # Build the BibTeX entry
    # Citation key is DOI with / replaced by @
    citation_key = doi.replace("/", "@")
    lines = [f"@article{{{citation_key},"]

    for key, val in fields:
        if val is not None and val != "":
            lines.append(f"  {key} = {{{val}}},")

    # Remove trailing comma on the last field line
    if len(lines) > 1 and lines[-1].endswith(","):
        lines[-1] = lines[-1][:-1]

    lines.append("}")

    bibtex = "\n".join(lines)

    # Write to disk
    output_path = Path(output_path)
    output_path.write_text(bibtex, encoding="utf-8")

    return bibtex
