"""Tests for DOI operations in anthology.anthology.doi."""

import re

from anthology.anthology.doi import (  # type: ignore[import-not-found]
    DOI_PREFIX,
    DOI_SUFFIX_LENGTH,
    generate_doi,
    is_doi_placeholder,
)


class TestIsDOIPlaceholder:
    """Tests for the is_doi_placeholder function."""

    def test_empty_string_is_placeholder(self):
        """Test that empty string is considered a placeholder."""
        assert is_doi_placeholder("") is True
        assert is_doi_placeholder("   ") is True

    def test_common_placeholders(self):
        """Test common placeholder patterns."""
        assert is_doi_placeholder("00000/00000") is True
        assert is_doi_placeholder("0") is True
        assert is_doi_placeholder("00000") is True
        assert is_doi_placeholder("XXXXX") is True

    def test_zeros_and_slashes(self):
        """Test strings with only zeros, slashes, and @ symbols."""
        assert is_doi_placeholder("000/000") is True
        assert is_doi_placeholder("0000@0000") is True
        assert is_doi_placeholder("///@@@") is True

    def test_valid_doi_not_placeholder(self):
        """Test that valid DOIs are not considered placeholders."""
        assert is_doi_placeholder("10.1234/abcd") is False
        assert is_doi_placeholder("10.63744/abc123") is False
        assert is_doi_placeholder("10.1000/xyz") is False

    def test_whitespace_trimming(self):
        """Test that whitespace is properly trimmed."""
        assert is_doi_placeholder("  00000  ") is True
        assert is_doi_placeholder("  10.1234/abcd  ") is False


class TestGenerateDOI:
    """Tests for the generate_doi function."""

    def test_default_parameters(self):
        """Test DOI generation with default parameters."""
        doi = generate_doi()
        assert doi.startswith(f"{DOI_PREFIX}/")
        suffix = doi.split("/", 1)[1]
        assert len(suffix) == DOI_SUFFIX_LENGTH

    def test_custom_prefix(self):
        """Test DOI generation with custom prefix."""
        custom_prefix = "10.12345"
        doi = generate_doi(prefix=custom_prefix)
        assert doi.startswith(f"{custom_prefix}/")

    def test_custom_suffix_length(self):
        """Test DOI generation with custom suffix length."""
        custom_length = 8
        doi = generate_doi(suffix_length=custom_length)
        suffix = doi.split("/", 1)[1]
        assert len(suffix) == custom_length

    def test_suffix_starts_with_letter(self):
        """Test that suffix starts with a letter."""
        doi = generate_doi()
        suffix = doi.split("/", 1)[1]
        assert suffix[0].isalpha()

    def test_suffix_alphanumeric(self):
        """Test that suffix contains only alphanumeric characters."""
        doi = generate_doi()
        suffix = doi.split("/", 1)[1]
        assert suffix.isalnum()

    def test_no_confusing_characters(self):
        """Test that suffix doesn't contain confusing characters O and l."""
        # Generate many DOIs to increase confidence
        for _ in range(100):
            doi = generate_doi()
            suffix = doi.split("/", 1)[1]
            assert "O" not in suffix  # Capital O
            assert "l" not in suffix  # Lowercase L

    def test_uniqueness(self):
        """Test that generated DOIs are unique."""
        dois = [generate_doi() for _ in range(100)]
        # All DOIs should be unique
        assert len(dois) == len(set(dois))

    def test_format_pattern(self):
        """Test that generated DOI matches expected format."""
        doi = generate_doi()
        # Should match pattern: prefix/suffix
        pattern = r"^\d+\.\d+/[A-Za-z][A-Za-z0-9]+$"
        assert re.match(pattern, doi)


class TestDOIConstants:
    """Tests for DOI module constants."""

    def test_doi_prefix_format(self):
        """Test that DOI_PREFIX has the expected format."""
        assert DOI_PREFIX.startswith("10.")
        assert "." in DOI_PREFIX

    def test_doi_suffix_length_positive(self):
        """Test that DOI_SUFFIX_LENGTH is positive."""
        assert DOI_SUFFIX_LENGTH > 0
        assert isinstance(DOI_SUFFIX_LENGTH, int)
