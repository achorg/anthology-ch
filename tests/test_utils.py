"""Tests for utility functions in anthology.anthology.utils."""

import pytest

from anthology.anthology.utils import (  # type: ignore[import-not-found]
    convert_latex_to_unicode,
    slugify,
    strip_html_tags,
)


class TestSlugify:
    """Tests for the slugify function."""

    def test_basic_slugification(self):
        """Test basic text to slug conversion."""
        assert slugify("Hello World", 20) == "hello-world"
        assert slugify("The Quick Brown Fox", 20) == "the-quick-brown-fox"

    def test_removes_common_words(self):
        """Test that common words like 'the', 'and', 'a', 'an' are removed when surrounded by spaces."""
        # Note: only removes when surrounded by spaces, not at beginning/end
        assert slugify("The Cat and the Dog", 30) == "the-cat-dog"
        assert slugify("Cat and Dog", 30) == "cat-dog"
        assert slugify("A Brief History", 30) == "a-brief-history"
        assert slugify("Brief History", 30) == "brief-history"

    def test_handles_diacritics(self):
        """Test that diacritics are removed."""
        assert slugify("Café résumé", 20) == "cafe-resume"
        assert slugify("Naïve", 20) == "naive"

    def test_handles_special_characters(self):
        """Test that special characters are replaced with spaces/dashes."""
        assert slugify("Hello & World!", 20) == "hello-world"
        assert slugify("Test: A Study", 20) == "test-study"
        assert slugify("Foo/Bar", 20) == "foo-bar"

    def test_respects_max_width(self):
        """Test that output is truncated at word boundaries to fit max_width."""
        result = slugify("The Quick Brown Fox Jumps", 10)
        assert len(result) <= 10
        assert result == "the-quick"  # First two words that fit

        result = slugify("Hello World Test", 11)
        assert len(result) <= 11
        assert result == "hello-world"  # Two words fit

    def test_no_partial_words(self):
        """Test that words are never truncated in the middle."""
        result = slugify("Hello World", 8)
        # Should only include "hello" (5 chars), not "hello-wo"
        assert result == "hello"
        assert "wo" not in result  # No partial words

    def test_empty_string(self):
        """Test handling of empty string."""
        assert slugify("", 20) == ""

    def test_only_special_characters(self):
        """Test string with only special characters."""
        assert slugify("!!!@@@###", 20) == ""

    def test_max_width_zero(self):
        """Test with max_width of 0."""
        assert slugify("Hello World", 0) == ""

    def test_max_width_type_error(self):
        """Test that non-integer max_width raises TypeError."""
        with pytest.raises(TypeError):
            slugify("Hello World", "20")  # type: ignore[arg-type]  # String instead of int

    def test_multiple_spaces_collapse(self):
        """Test that multiple spaces collapse to single dash."""
        assert slugify("Hello    World", 20) == "hello-world"


class TestConvertLatexToUnicode:
    """Tests for the convert_latex_to_unicode function."""

    def test_triple_dash_to_em_dash(self):
        """Test that triple dash is converted to em dash."""
        assert convert_latex_to_unicode("Hello---World") == "Hello—World"
        assert convert_latex_to_unicode("1990---2000") == "1990—2000"

    def test_no_changes_needed(self):
        """Test that strings without LaTeX markup are unchanged."""
        assert convert_latex_to_unicode("Hello World") == "Hello World"
        assert convert_latex_to_unicode("Plain text") == "Plain text"

    def test_multiple_triple_dashes(self):
        """Test handling of multiple triple dashes."""
        assert convert_latex_to_unicode("A---B---C") == "A—B—C"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert convert_latex_to_unicode("") == ""


class TestStripHtmlTags:
    """Tests for the strip_html_tags function."""

    def test_removes_simple_tags(self):
        """Test removal of simple HTML tags."""
        assert strip_html_tags("<p>Hello</p>") == "Hello"
        assert strip_html_tags("<strong>Bold</strong>") == "Bold"

    def test_removes_nested_tags(self):
        """Test removal of nested HTML tags."""
        assert strip_html_tags("<p>Hello <strong>world</strong></p>") == "Hello world"
        assert strip_html_tags("<div><span>Test</span></div>") == "Test"

    def test_removes_tags_with_attributes(self):
        """Test removal of tags with attributes."""
        assert strip_html_tags('<a href="test.html">Link</a>') == "Link"
        assert strip_html_tags('<p class="test">Text</p>') == "Text"

    def test_collapses_whitespace(self):
        """Test that multiple spaces and newlines are collapsed."""
        assert strip_html_tags("<p>Hello    World</p>") == "Hello World"
        assert strip_html_tags("<p>Line1\n\nLine2</p>") == "Line1 Line2"

    def test_plain_text_unchanged(self):
        """Test that plain text without tags is unchanged (except whitespace)."""
        assert strip_html_tags("Plain text") == "Plain text"

    def test_empty_string(self):
        """Test handling of empty string."""
        assert strip_html_tags("") == ""

    def test_self_closing_tags(self):
        """Test handling of self-closing tags."""
        assert strip_html_tags("Text<br/>More text") == "TextMore text"
        assert strip_html_tags("Line<hr />Break") == "LineBreak"

    def test_complex_html(self):
        """Test with more complex HTML structure."""
        html = """
        <div class="content">
            <h1>Title</h1>
            <p>Paragraph with <em>emphasis</em> and <strong>bold</strong>.</p>
        </div>
        """
        result = strip_html_tags(html)
        assert "<" not in result
        assert ">" not in result
        assert "Title" in result
        assert "Paragraph" in result
        assert "emphasis" in result
        assert "bold" in result
