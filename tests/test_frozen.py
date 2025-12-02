"""Tests for frozen volume functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from anthology.anthology.paper import Paper


class TestFrozenVolume:
    """Tests for frozen volume page number handling."""

    def test_add_metadata_skips_page_numbers_when_frozen(self):
        """Test that add_metadata does not update page numbers for frozen volumes."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            paper_tex = output_dir / "paper.tex"

            # Create a mock paper.tex file with existing page numbers
            initial_content = """
\\documentclass{article}
\\pubvolume{1}
\\pubyear{2025}
\\conferencename{Test Conference}
\\conferenceeditors{Test Editor}
\\pagestart{5}
\\pageend{10}
\\begin{document}
Test content
\\end{document}
"""
            paper_tex.write_text(initial_content)

            # Create a Paper instance with frozen=true in volume_meta
            paper = Paper.__new__(Paper)
            paper.output_dir = output_dir
            paper.volume_meta = {
                "pubvolume": "1",
                "pubyear": "2025",
                "conferencename": "Test Conference",
                "conferenceeditors": "Test Editor",
                "frozen": True,
            }

            # Call add_metadata with different page numbers
            paper.add_metadata(100, 120)

            # Read the updated file
            updated_content = paper_tex.read_text()

            # Verify that page numbers were NOT changed (still 5 and 10)
            assert "\\pagestart{5}" in updated_content
            assert "\\pageend{10}" in updated_content
            assert "\\pagestart{100}" not in updated_content
            assert "\\pageend{120}" not in updated_content

    def test_add_metadata_updates_page_numbers_when_not_frozen(self):
        """Test that add_metadata updates page numbers for non-frozen volumes."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            paper_tex = output_dir / "paper.tex"

            # Create a mock paper.tex file with existing page numbers
            initial_content = """
\\documentclass{article}
\\pubvolume{1}
\\pubyear{2025}
\\conferencename{Test Conference}
\\conferenceeditors{Test Editor}
\\pagestart{5}
\\pageend{10}
\\begin{document}
Test content
\\end{document}
"""
            paper_tex.write_text(initial_content)

            # Create a Paper instance with frozen=false in volume_meta
            paper = Paper.__new__(Paper)
            paper.output_dir = output_dir
            paper.volume_meta = {
                "pubvolume": "1",
                "pubyear": "2025",
                "conferencename": "Test Conference",
                "conferenceeditors": "Test Editor",
                "frozen": False,
            }

            # Call add_metadata with different page numbers
            paper.add_metadata(100, 120)

            # Read the updated file
            updated_content = paper_tex.read_text()

            # Verify that page numbers WERE changed (now 100 and 120)
            assert "\\pagestart{100}" in updated_content
            assert "\\pageend{120}" in updated_content
            assert "\\pagestart{5}" not in updated_content
            assert "\\pageend{10}" not in updated_content

    def test_add_metadata_updates_page_numbers_when_frozen_not_specified(self):
        """Test that add_metadata updates page numbers when frozen key is not present."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            paper_tex = output_dir / "paper.tex"

            # Create a mock paper.tex file with existing page numbers
            initial_content = """
\\documentclass{article}
\\pubvolume{1}
\\pubyear{2025}
\\conferencename{Test Conference}
\\conferenceeditors{Test Editor}
\\pagestart{5}
\\pageend{10}
\\begin{document}
Test content
\\end{document}
"""
            paper_tex.write_text(initial_content)

            # Create a Paper instance without frozen key in volume_meta
            paper = Paper.__new__(Paper)
            paper.output_dir = output_dir
            paper.volume_meta = {
                "pubvolume": "1",
                "pubyear": "2025",
                "conferencename": "Test Conference",
                "conferenceeditors": "Test Editor",
            }

            # Call add_metadata with different page numbers
            paper.add_metadata(100, 120)

            # Read the updated file
            updated_content = paper_tex.read_text()

            # Verify that page numbers WERE changed (defaults to not frozen)
            assert "\\pagestart{100}" in updated_content
            assert "\\pageend{120}" in updated_content
            assert "\\pagestart{5}" not in updated_content
            assert "\\pageend{10}" not in updated_content
