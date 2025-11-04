"""LaTeX metadata extraction and parsing utilities."""

import re
from typing import Any, Dict, List, Optional, Tuple


class LaTeXMetadataExtractor:
    """
    Extract metadata from LaTeX source files.

    This class provides methods to parse LaTeX files and extract structured
    metadata including titles, authors, affiliations, keywords, and publication
    information. It handles complex LaTeX structures with balanced braces and
    brackets.
    """

    def __init__(self) -> None:
        """Initialize the LaTeX metadata extractor with regex patterns."""
        # Patterns for different types of LaTeX macros
        self.patterns = {
            # Simple macros: \title{content}
            "simple": r"\\(\w+)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
            # Macros with optional parameters: \author[option]{content}
            "with_optional": r"\\(\w+)(?:\[([^\]]*)\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}",
            # Macros with multiple braced parameters: \affiliation{1}{content}
            "multiple_braced": r"\\(\w+)(\{[^{}]*\})+",
            # Complex pattern for author-like macros with trailing optional parts
            "complex_author": r"\\(\w+)(?:\[([^\]]*)\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}(?:\s*\[([^\]]*)\])?",
        }

    def extract_balanced_braces(
        self, text: str, start_pos: int
    ) -> Tuple[Optional[str], int]:
        """
        Extract content within balanced braces starting at start_pos.

        Args:
            text: The text to search
            start_pos: Position where the opening brace should be

        Returns:
            Tuple of (extracted content or None, position after closing brace)
        """
        if start_pos >= len(text) or text[start_pos] != "{":
            return None, start_pos

        brace_count = 0
        content_start = start_pos + 1
        i = start_pos

        while i < len(text):
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    return text[content_start:i], i + 1
            elif text[i] == "\\" and i + 1 < len(text):
                # Skip escaped characters
                i += 1
            i += 1

        return None, start_pos

    def extract_balanced_brackets(
        self, text: str, start_pos: int
    ) -> Tuple[Optional[str], int]:
        """
        Extract content within balanced brackets starting at start_pos.

        Handles multi-line content within brackets.

        Args:
            text: The text to search
            start_pos: Position where the opening bracket should be

        Returns:
            Tuple of (extracted content or None, position after closing bracket)
        """
        if start_pos >= len(text) or text[start_pos] != "[":
            return None, start_pos

        bracket_count = 0
        content_start = start_pos + 1
        i = start_pos

        while i < len(text):
            if text[i] == "[":
                bracket_count += 1
            elif text[i] == "]":
                bracket_count -= 1
                if bracket_count == 0:
                    return text[content_start:i], i + 1
            elif text[i] == "\\" and i + 1 < len(text):
                # Skip escaped characters
                i += 1
            i += 1

        return None, start_pos

    def parse_key_value_pairs(self, content: str) -> Dict[str, Any]:
        """
        Parse key-value pairs from optional parameter content.

        Handles content like 'orcid=123, email=abc' and also boolean flags.

        Args:
            content: String containing comma-separated key=value pairs

        Returns:
            Dictionary mapping keys to values (or True for boolean flags)

        Examples:
            >>> parse_key_value_pairs("orcid=0000-0001-2345-6789, email=test@example.com")
            {'orcid': '0000-0001-2345-6789', 'email': 'test@example.com'}
        """
        if not content:
            return {}

        pairs = {}
        # Split by comma, but be careful about nested structures
        parts = []
        current_part = ""
        paren_count = 0

        for char in content:
            if char == "," and paren_count == 0:
                parts.append(current_part.strip())
                current_part = ""
            else:
                if char in "([{":
                    paren_count += 1
                elif char in ")]}":
                    paren_count -= 1
                current_part += char

        if current_part.strip():
            parts.append(current_part.strip())

        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                pairs[key.strip()] = value.strip()
            elif part.strip():
                # Handle boolean flags
                pairs[part.strip()] = True

        return pairs

    def extract_author_macros(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract author macros with their complex structure.

        Parses \\author commands including optional affiliation numbers
        and metadata like ORCID iDs and email addresses.

        Args:
            text: LaTeX source text containing \\author commands

        Returns:
            List of dictionaries, each containing:
            - name: Author name
            - affiliation_numbers: List of affiliation number strings
            - metadata: Dictionary of additional metadata (orcid, email, etc.)
        """
        authors = []

        # Pattern to find author macros
        author_pattern = (
            r"\\author(?:\[([^\]]*)\])?\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        )

        matches = list(re.finditer(author_pattern, text, re.DOTALL))

        for match in matches:
            author_data = {
                "name": match.group(2).strip(),
                "affiliation_numbers": [],
                "metadata": {},
            }

            # Parse affiliation number from first optional parameter
            if match.group(1):
                affiliation_nums = match.group(1).strip()
                if affiliation_nums:
                    # Handle multiple affiliations like [1,2,3]
                    author_data["affiliation_numbers"] = [
                        num.strip() for num in affiliation_nums.split(",")
                    ]

            # Look for optional metadata block after the author name
            pos = match.end()
            while pos < len(text) and text[pos].isspace():
                pos += 1

            if pos < len(text) and text[pos] == "[":
                metadata_content, new_pos = self.extract_balanced_brackets(text, pos)
                if metadata_content:
                    author_data["metadata"] = self.parse_key_value_pairs(
                        metadata_content
                    )

            authors.append(author_data)

        return authors

    def extract_affiliation_macros(self, text: str) -> List[Dict[str, str]]:
        """
        Extract affiliation macros with number and text.

        Parses \\affiliation{number}{text} commands.

        Args:
            text: LaTeX source text containing \\affiliation commands

        Returns:
            List of dictionaries with 'number' and 'text' keys
        """
        affiliations = []

        # Pattern for \affiliation{number}{text}
        affiliation_pattern = (
            r"\\affiliation\s*\{([^}]*)\}\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        )

        matches = re.finditer(affiliation_pattern, text, re.DOTALL)

        for match in matches:
            affiliations.append(
                {"number": match.group(1).strip(), "text": match.group(2).strip()}
            )

        return affiliations

    def extract_simple_macros(
        self, text: str, macro_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract simple macros like \\title{content}.

        Args:
            text: LaTeX source text
            macro_names: List of macro names to extract (default: common metadata macros)

        Returns:
            Dictionary mapping macro names to their content.
            If a macro appears multiple times, value is a list.
        """
        if macro_names is None:
            macro_names = [
                "title",
                "keywords",
                "pubyear",
                "pubvolume",
                "pagestart",
                "pageend",
                "doi",
                "addbibresource",
            ]

        results = {}

        for macro_name in macro_names:
            pattern = f"\\\\{re.escape(macro_name)}\\s*\\{{([^{{}}]*(?:\\{{[^{{}}]*\\}}[^{{}}]*)*)}}"
            matches = re.findall(pattern, text, re.DOTALL)

            if matches:
                if len(matches) == 1:
                    results[macro_name] = matches[0].strip()
                else:
                    results[macro_name] = [match.strip() for match in matches]

        return results

    def extract_commented_macros(self, text: str) -> Dict[str, str]:
        """
        Extract commented out macros (starting with %).

        Args:
            text: LaTeX source text

        Returns:
            Dictionary mapping macro names to their content
        """
        commented = {}

        # Pattern for commented macros like %\conferencename{...}
        pattern = r"%\\(\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            macro_name = match.group(1)
            content = match.group(2).strip()
            commented[macro_name] = content

        return commented

    def extract_all_metadata(self, latex_content: str) -> Dict[str, Any]:
        """
        Extract all types of metadata from LaTeX content.

        This is the main entry point for extracting metadata. It combines
        results from all extraction methods.

        Args:
            latex_content: Complete LaTeX source text

        Returns:
            Dictionary containing:
            - title: Paper title
            - authors: List of author dictionaries
            - affiliations: List of affiliation dictionaries
            - keywords: Keywords string
            - publication_info: Dictionary of publication metadata
            - commented_macros: Dictionary of commented-out macros
        """

        metadata = {
            "title": None,
            "authors": [],
            "affiliations": [],
            "keywords": None,
            "publication_info": {},
            "commented_macros": {},
        }

        # Extract simple macros
        simple_macros = self.extract_simple_macros(latex_content)

        # Organize simple macros
        if "title" in simple_macros:
            metadata["title"] = simple_macros["title"]
        if "keywords" in simple_macros:
            metadata["keywords"] = simple_macros["keywords"]

        # Publication information
        pub_fields = [
            "pubyear",
            "pubvolume",
            "pagestart",
            "pageend",
            "doi",
            "addbibresource",
        ]
        pub_info: Dict[str, Any] = metadata["publication_info"]  # type: ignore
        for field in pub_fields:
            if field in simple_macros:
                pub_info[field] = simple_macros[field]

        # Extract complex structures
        metadata["authors"] = self.extract_author_macros(latex_content)
        metadata["affiliations"] = self.extract_affiliation_macros(latex_content)
        metadata["commented_macros"] = self.extract_commented_macros(latex_content)

        return metadata

    def parse_latex_file(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a LaTeX file and extract metadata.

        Args:
            file_path: Path to the LaTeX file

        Returns:
            Dictionary of extracted metadata, or error information if parsing fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            return self.extract_all_metadata(content)
        except FileNotFoundError:
            return {"error": f"File {file_path} not found"}
        except Exception as e:
            return {"error": f"Error reading file: {str(e)}"}

    def format_authors_with_affiliations(
        self, metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Combine author information with their affiliations.

        Args:
            metadata: Metadata dictionary from extract_all_metadata()

        Returns:
            List of author dictionaries with affiliations expanded:
            - name: Author name
            - affiliations: List of affiliation dicts with 'number' and 'text'
            - metadata: Additional author metadata (orcid, email, etc.)
        """
        formatted_authors = []

        # Create affiliation lookup
        affiliation_lookup = {
            aff["number"]: aff["text"] for aff in metadata.get("affiliations", [])
        }

        for author in metadata.get("authors", []):
            formatted_author = {
                "name": author["name"],
                "affiliations": [],
                "metadata": author.get("metadata", {}),
            }

            # Add affiliation text for each number
            for aff_num in author.get("affiliation_numbers", []):
                if aff_num in affiliation_lookup:
                    formatted_author["affiliations"].append(
                        {"number": aff_num, "text": affiliation_lookup[aff_num]}
                    )

            formatted_authors.append(formatted_author)

        return formatted_authors
