"""Paper class representing a single journal article."""

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pypdf import PdfReader

from .bibtex import write_bibtex_article
from .doi import DOI_PREFIX, DOI_SUFFIX_LENGTH, generate_doi, is_doi_placeholder
from .latex import fill_value, run_xelatex
from .latex_parser import LaTeXMetadataExtractor
from .metadata import load_paper_metadata, save_paper_metadata
from .utils import convert_latex_to_unicode, slugify


def fix_table_figure_labels(content: str) -> str:
    """
    Move \\label commands to immediately after \\caption in table and figure environments.

    Pandoc-crossref requires labels to immediately follow captions for proper numbering.
    This function finds table/figure environments where content exists between \\caption
    and \\label, and moves the label to immediately after the caption.

    Args:
        content: LaTeX source code

    Returns:
        Modified LaTeX with labels repositioned
    """
    # Pattern to match table or figure environments
    # Captures: 1) environment type, 2) content before caption, 3) caption,
    #          4) content between caption and label, 5) label, 6) rest of content
    pattern = r"(\\begin\{(?:table|figure)\}[^\n]*\n)(.*?)(\\caption\{(?:[^{}]|\{[^{}]*\})*\})\s*(.*?)(\\label\{[^}]+\})(.*?)(\\end\{(?:table|figure)\})"

    def replacer(match):
        begin = match.group(1)
        before_caption = match.group(2)
        caption = match.group(3)
        between = match.group(4)
        label = match.group(5)
        after_label = match.group(6)
        end = match.group(7)

        # Check if there's actual content between caption and label (not just whitespace)
        if between.strip():
            # Move label to immediately after caption, keep the between content after label
            return f"{begin}{before_caption}{caption}\n  {label}\n{between}{after_label}{end}"
        else:
            # Label is already right after caption, no change needed
            return match.group(0)

    # Apply the transformation repeatedly until no more matches (handles nested cases)
    prev_content = None
    while prev_content != content:
        prev_content = content
        content = re.sub(pattern, replacer, content, flags=re.DOTALL)

    return content


class Paper:
    """
    Represents a single journal article in the anthology.

    A Paper manages all operations related to a single article, including:
    - LaTeX compilation
    - Metadata extraction
    - HTML generation
    - BibTeX citation creation
    - File organization

    Attributes:
        input_dir: Path to the input directory (None if loaded from output)
        output_dir: Path to the output directory for generated files
        paperid: Numeric ID of the paper (from directory name)
        volumeid: Numeric ID of the volume (from parent directory name)
        volume: Volume directory name
        volume_meta: Dictionary of volume metadata
        paper_order: Order of paper within the volume
        include_html: Whether to include full article text in HTML output
    """

    def __init__(
        self,
        input_dir: Path,
        volume_meta: Dict,
        paper_order: int = 1,
        include_html: bool = True,
    ):
        """
        Initialize a Paper object from input directory.

        Args:
            input_dir: Path to the paper's input directory
            volume_meta: Dictionary containing volume metadata
            paper_order: Order of paper within the volume (default: 1)
            include_html: Whether to include full article text in HTML (default: True)
        """
        self.input_dir = input_dir
        self.paperid = int(input_dir.name[-3:])
        self.volumeid = int(input_dir.parent.name[-3:])
        self.volume = input_dir.parent.name[-9:]
        self.volume_meta = volume_meta
        self.paper_order = paper_order
        self.include_html = include_html

        # Extract title from paper.tex and create slugified directory name
        paper_file = input_dir / "paper.tex"
        if paper_file.exists():
            paper_content = paper_file.read_text()
            extractor = LaTeXMetadataExtractor()
            pmeta = extractor.extract_all_metadata(paper_content)
            title = pmeta.get("title", "")
            title_slug = slugify(title, max_width=50)

            # Use slugified title for output directory name
            volume_dir = input_dir.parent.name
            self.output_dir = Path("docs/volumes") / volume_dir / title_slug
        else:
            # Fallback to original behavior if paper.tex doesn't exist
            self.output_dir = Path("docs/volumes") / input_dir.relative_to("input")

    @classmethod
    def from_output_dir(cls, output_dir: Path) -> Optional["Paper"]:
        """
        Create a Paper object from an output directory with saved metadata.

        This allows rebuilding papers without access to the input directory.

        Args:
            output_dir: Path to the paper's output directory

        Returns:
            Paper object or None if metadata file is missing
        """
        # Load saved metadata
        meta = load_paper_metadata(output_dir)
        if not meta:
            return None

        # Create a Paper instance with minimal initialization
        paper = cls.__new__(cls)
        paper.input_dir = Path(meta["input_dir"]) if meta.get("input_dir") else None
        paper.output_dir = output_dir
        paper.paperid = meta["paperid"]
        paper.volumeid = meta["volumeid"]
        paper.volume = meta["volume"]
        paper.volume_meta = meta["volume_meta"]
        paper.paper_order = meta.get("paper_order", 1)
        paper.include_html = meta.get("include_html", True)

        return paper

    def __str__(self) -> str:
        """Return string representation of the Paper object."""
        return f"Paper Object: {self.output_dir} ({self.volumeid})"

    def __lt__(self, other: "Paper") -> bool:
        """
        Compare papers for sorting by volume ID and paper ID.

        Args:
            other: Another Paper object to compare with

        Returns:
            True if this paper should sort before the other
        """
        if not isinstance(other, Paper):
            return NotImplemented
        return (self.volumeid, self.paperid) < (other.volumeid, other.paperid)

    def validate_input(self) -> None:
        """
        Validate that required input files exist.

        Raises:
            FileNotFoundError: If paper.tex or bibliography.bib is missing
        """
        tex_path = self.input_dir / "paper.tex"
        bib_path = self.input_dir / "bibliography.bib"

        if not tex_path.exists():
            raise FileNotFoundError(f"Paper path does not exist: {tex_path}")

        if not bib_path.exists():
            raise FileNotFoundError(f"Bibliography path does not exist: {bib_path}")

    def add_doi(self, verbose: bool = False) -> None:
        """
        Add a DOI to the paper if it has a placeholder DOI.

        Checks if the current DOI is a placeholder and generates a new
        random DOI if needed.

        Args:
            verbose: If True, print confirmation message when DOI is added
        """
        paper_file = self.input_dir / "paper.tex"
        paper_content = paper_file.read_text()
        extractor = LaTeXMetadataExtractor()
        pmeta = extractor.extract_all_metadata(paper_content)
        current_doi = pmeta.get("publication_info", {}).get("doi", "")

        if is_doi_placeholder(current_doi):
            new_doi = generate_doi(DOI_PREFIX, DOI_SUFFIX_LENGTH)
            updated_paper = fill_value(paper_content, "doi", new_doi)
            paper_file.write_text(updated_paper)
            if verbose:
                print(f"  Added DOI: {new_doi}")

    def copy_to_output(self, verbose: bool = False, order: int = 1) -> None:
        """
        Copy input files to output directory and process figures.

        Copies paper.tex and bibliography.bib to the output directory.
        Also handles figure processing:
        - Converts PDF figures to PNG at 300dpi
        - Updates \\includegraphics paths
        - Applies text transformations
        - Sets paper order number

        Args:
            verbose: If True, print detailed progress information
            order: Paper order number within the volume (default: 1)
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.input_dir / "paper.tex", self.output_dir / "paper.tex")
        shutil.copy2(
            self.input_dir / "bibliography.bib", self.output_dir / "bibliography.bib"
        )

        paper_file = self.input_dir / "paper.tex"
        paper_content = paper_file.read_text()

        # Apply text transformations
        paper_content = paper_content.replace("\\paragraph", "\n\n\\noindent\n\\textbf")
        paper_content = paper_content.replace("\\textdaggerdbl", "‡")

        # Fix table/figure labels for pandoc-crossref compatibility
        # Move labels to immediately after captions
        paper_content = fix_table_figure_labels(paper_content)

        # Set paper order number
        paper_content = fill_value(paper_content, "paperorder", str(order))

        # Find all figure references
        includegraphics_pattern = r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"
        matches = re.findall(includegraphics_pattern, paper_content)

        if matches:
            # Create figures directory in output
            figures_dir = self.output_dir / "figures"
            figures_dir.mkdir(exist_ok=True)

            # Process each figure reference
            for figure_path in matches:
                # Clean the path
                figure_path = figure_path.strip()

                # Find the actual file in the input directory
                source_file = self.input_dir / figure_path

                if source_file.exists() and source_file.is_file():
                    filename = source_file.name

                    # Check if this is a PDF file that needs conversion
                    if source_file.suffix.lower() == ".pdf":
                        # Convert PDF to PNG using ghostscript at 300dpi
                        png_filename = source_file.stem + ".png"
                        dest_file = figures_dir / png_filename

                        # Use ghostscript to convert PDF to PNG at 300dpi
                        gs_result = subprocess.run(
                            [
                                "gs",
                                "-dNOPAUSE",
                                "-dBATCH",
                                "-sDEVICE=png16m",
                                "-r300",  # 300 DPI
                                "-sOutputFile=" + str(dest_file),
                                str(source_file),
                            ],
                            capture_output=True,
                            text=True,
                        )

                        if gs_result.returncode != 0:
                            if verbose:
                                print(
                                    f"  Warning: Failed to convert {source_file} to PNG: {gs_result.stderr}"
                                )
                            # Fall back to copying the PDF as-is
                            dest_file = figures_dir / filename
                            shutil.copy2(source_file, dest_file)
                            new_path = f"figures/{filename}"
                        else:
                            # Successfully converted to PNG
                            new_path = f"figures/{png_filename}"
                    else:
                        # Not a PDF, just copy the file
                        dest_file = figures_dir / filename
                        shutil.copy2(source_file, dest_file)
                        new_path = f"figures/{filename}"

                    # Update the path in paper content
                    old_pattern = (
                        r"(\\includegraphics(?:\[[^\]]*\])?)\{"
                        + re.escape(figure_path)
                        + r"\}"
                    )
                    new_replacement = r"\1{" + new_path + r"}"
                    paper_content = re.sub(old_pattern, new_replacement, paper_content)

        # Write updated paper content
        output_paper_file = self.output_dir / "paper.tex"
        output_paper_file.write_text(paper_content)

        # Save metadata for future builds without input directory
        self.paper_order = order  # Update paper order
        save_paper_metadata(
            output_dir=self.output_dir,
            input_dir=self.input_dir,
            paperid=self.paperid,
            volumeid=self.volumeid,
            volume=self.volume,
            volume_meta=self.volume_meta,
            paper_order=order,
            include_html=self.include_html,
        )

    def compile_xelatex(self, verbose: bool = False) -> bool:
        """
        Compile the paper using XeLaTeX.

        Args:
            verbose: If True, show LaTeX compilation output

        Returns:
            True if compilation succeeded, False otherwise
        """
        return run_xelatex(self.output_dir, verbose=verbose)

    def clean_xelatex(self) -> None:
        """
        Remove LaTeX auxiliary files from output directory.

        Removes files with extensions like .aux, .log, .out, etc.
        and directories like _minted.
        """
        extensions = {
            ".aux",
            ".log",
            ".out",
            ".toc",
            ".lof",
            ".lot",
            ".bbl",
            ".bcf",
            ".blg",
            ".run.xml",
            ".fls",
            ".fdb_latexmk",
            ".synctex.gz",
            ".dvi",
            ".bak",
            "-blx.bib",
            ".spl",
        }
        dirs_to_delete = {"_minted"}

        for item in self.output_dir.iterdir():
            if item.is_file() and any(
                item.name.lower().endswith(ext) for ext in extensions
            ):
                item.unlink()
            elif item.is_dir() and item.name in dirs_to_delete:
                shutil.rmtree(item, ignore_errors=True)

    def get_latex_metadata(self) -> Dict:
        """
        Extract metadata from the paper's LaTeX source.

        Returns:
            Dictionary containing title, authors, affiliations, publication info, etc.
        """
        paper_file = self.output_dir / "paper.tex"
        paper_content = paper_file.read_text()
        extractor = LaTeXMetadataExtractor()
        pmeta = extractor.extract_all_metadata(paper_content)
        return pmeta

    def move_pdf(self) -> None:
        """
        Rename the compiled PDF to use the DOI as filename.

        Renames paper.pdf to {doi}.pdf where / in DOI is replaced with @.
        """
        pmeta = self.get_latex_metadata()
        current_doi = pmeta.get("publication_info", {}).get("doi", "")

        src = self.output_dir / "paper.pdf"
        dst = self.output_dir / f"{current_doi.replace('/', '@')}.pdf"
        if src.exists():
            shutil.move(str(src), str(dst))

    def num_pages(self) -> int:
        """
        Count the number of pages in the compiled PDF.

        Returns:
            Number of pages in paper.pdf
        """
        pdf_path = self.output_dir / "paper.pdf"
        num_pages = len(PdfReader(pdf_path).pages)
        return num_pages

    def add_metadata(self, page_start: int, end_page: int) -> None:
        """
        Add publication metadata to the paper's LaTeX source.

        Updates the paper.tex file with volume, year, conference, editor,
        and page number information.

        Args:
            page_start: Starting page number in the volume
            end_page: Ending page number in the volume
        """
        paper_file = self.output_dir / "paper.tex"
        paper_content = paper_file.read_text()

        updated_paper = paper_content
        updated_paper = fill_value(
            updated_paper, "pubvolume", self.volume_meta["pubvolume"]
        )
        updated_paper = fill_value(
            updated_paper, "pubyear", self.volume_meta["pubyear"]
        )
        updated_paper = fill_value(
            updated_paper, "conferencename", self.volume_meta["conferencename"]
        )
        updated_paper = fill_value(
            updated_paper, "conferenceeditors", self.volume_meta["conferenceeditors"]
        )
        updated_paper = fill_value(updated_paper, "pagestart", str(page_start))
        updated_paper = fill_value(updated_paper, "pageend", str(end_page))
        paper_file.write_text(updated_paper)

    def create_bibtex(self) -> None:
        """
        Generate a BibTeX citation file for the paper.

        Creates a .bib file named {doi}.bib in the output directory.
        """
        pmeta = self.get_latex_metadata()
        doi = pmeta.get("publication_info", {}).get("doi", "")

        write_bibtex_article(
            title=pmeta["title"],
            volume=self.volume_meta["pubvolume"],
            authors=[x["name"] for x in pmeta["authors"]],
            year=self.volume_meta["pubyear"],
            journal="Anthology for Computers and the Humanities",
            editors=self.volume_meta["conferenceeditors"],
            pages=f"{pmeta['publication_info']['pagestart']}--{pmeta['publication_info']['pageend']}",
            doi=doi,
            output_path=(self.output_dir / f"{doi.replace('/', '@')}.bib"),
        )

    def create_html(self, verbose: bool = False) -> None:
        """
        Generate an HTML version of the paper.

        Uses Pandoc to convert LaTeX to HTML, then wraps it in a template
        with metadata, author information, and citation data.

        Args:
            verbose: If True, print error messages from Pandoc
        """
        # Fix table/figure labels for pandoc-crossref compatibility
        # Move labels to immediately after captions
        paper_file = self.output_dir / "paper.tex"
        paper_content = paper_file.read_text()
        paper_content = fix_table_figure_labels(paper_content)
        paper_file.write_text(paper_content)

        pmeta = self.get_latex_metadata()
        doi = pmeta.get("publication_info", {}).get("doi", "")

        # Extract abstract directly from LaTeX source since Pandoc discards it
        paper_file = self.output_dir / "paper.tex"
        paper_content = paper_file.read_text()
        abstract_match = re.search(
            r"\\begin\{abstract\}(.*?)\\end\{abstract\}", paper_content, re.DOTALL
        )
        abstract_latex = abstract_match.group(1).strip() if abstract_match else ""

        cmd = [
            "pandoc",
            str(self.output_dir / "paper.tex"),
            "-f",
            "latex+smart+raw_tex",
            "-t",
            "html5",
            "--bibliography",
            str(self.output_dir / "bibliography.bib"),
            "--number-sections",
            "--syntax-highlighting=pygments",
            "--metadata",
            "reference-section-title=References",
            "--metadata",
            "abstract-class=abs",
            "--metadata",
            "abstract-title=Abstract",
            "--metadata",
            "tableTitle=Table",
            "--metadata",
            "listingTitle=Listing",
            "--metadata",
            "tableEqns=true",
            "--metadata",
            "listingEqns=true",
            "--metadata",
            "link-citations=true",
            "--filter",
            "pandoc-crossref",
            "--lua-filter",
            "docs/resources/combined-filters.lua",
            "--citeproc",
            "--csl=docs/resources/template-md/mla-numeric.csl",
            "--quiet",
        ]

        try:
            res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            if verbose:
                print("❌ Pandoc failed!")
                print("Return code:", e.returncode)
                print("STDOUT:\n", e.stdout)
                print("STDERR:\n", e.stderr)
            return

        html_fragment = res.stdout
        html_fragment.replace("---", "—")

        # Convert abstract from LaTeX to HTML and prepend to content
        abstract_html = ""
        if abstract_latex:
            try:
                # Use Pandoc to convert just the abstract from LaTeX to HTML
                abstract_result = subprocess.run(
                    ["pandoc", "-f", "latex", "-t", "html5"],
                    input=abstract_latex,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                abstract_html = f'<div class="abs"><span>Abstract</span>{abstract_result.stdout.strip()}</div>\n\n'
                # Prepend abstract to the full HTML content
                html_fragment = abstract_html + html_fragment
            except subprocess.CalledProcessError:
                # If abstract conversion fails, skip it
                pass

        # If include_html is False, we'll only include the abstract, not the full text
        if not self.include_html:
            # Only keep the abstract
            html_fragment = abstract_html

        # Prepare author data
        aff = {
            item["number"]: convert_latex_to_unicode(item["text"])
            for item in pmeta["affiliations"]
        }
        author_input = []
        for auth in pmeta["authors"]:
            affiliation_list: list = []
            npart: Dict[str, Any] = {
                "name": convert_latex_to_unicode(auth["name"]),
                "affiliation": affiliation_list,
            }
            if "orcid" in auth["metadata"]:
                npart["orcid"] = auth["metadata"]["orcid"]
            for aff_vals in auth["affiliation_numbers"]:
                affiliation_list.append(aff[aff_vals])
            npart["affiliation"] = ";".join(affiliation_list)
            author_input.append(npart)

        converted_affiliations = [
            {"number": item["number"], "text": convert_latex_to_unicode(item["text"])}
            for item in pmeta["affiliations"]
        ]

        converted_title = convert_latex_to_unicode(pmeta["title"])
        cite = f"<i>Anthology of Computers and the Humanities</i>, Vol. {pmeta['publication_info']['pubvolume']}, {self.volume_meta['pubyear']}, Pages {pmeta['publication_info']['pagestart']}-{pmeta['publication_info']['pageend']}."

        # Extract abstract for citation metadata from the LaTeX abstract we already extracted
        abstract_text_clean = (
            convert_latex_to_unicode(abstract_latex) if abstract_latex else ""
        )

        # Parse keywords into a list
        keywords_str = pmeta.get("keywords", "")
        keywords_list = (
            [kw.strip() for kw in keywords_str.split(",")] if keywords_str else []
        )

        # Prepare citation authors
        cite_authors = []
        for auth in pmeta["authors"]:
            name = auth["name"]
            name_parts = name.strip().split()
            if len(name_parts) > 1:
                first = " ".join(name_parts[:-1])
                last = name_parts[-1]
            else:
                first = ""
                last = name_parts[0] if name_parts else ""
            cite_authors.append({"first": first, "last": last})

        # Prepare citation editors
        cite_editors = []
        if (
            "conferenceeditors" in self.volume_meta
            and self.volume_meta["conferenceeditors"]
        ):
            editors_str = self.volume_meta["conferenceeditors"]
            editor_names = re.split(r"\s+and\s+|,\s*", editors_str)
            for editor_name in editor_names:
                editor_name = editor_name.strip()
                if editor_name:
                    name_parts = editor_name.split()
                    if len(name_parts) > 1:
                        first = " ".join(name_parts[:-1])
                        last = name_parts[-1]
                    else:
                        first = ""
                        last = name_parts[0] if name_parts else ""
                    cite_editors.append({"first": first, "last": last})

        # Construct URLs
        base_url = "https://anthology.ach.org"
        volume_path = f"vol{self.volumeid:04d}"
        paper_slug = self.output_dir.name

        cite_paper_url = f"{base_url}/volumes/{volume_path}/{paper_slug}/"
        cite_html_url = cite_paper_url
        cite_pdf_url = (
            f"{base_url}/volumes/{volume_path}/{paper_slug}/{doi.replace('/', '@')}.pdf"
        )

        # If include_html is False, only show abstract in content area
        if not self.include_html:
            # Extract just the abstract from html_fragment
            abstract_match = re.search(
                r'<div class="abs">(.*?)</div>', html_fragment, re.DOTALL
            )
            if abstract_match:
                # Keep only the abstract div
                html_fragment = f'<div class="abs">{abstract_match.group(1)}</div>'
            else:
                # No abstract found, show empty content
                html_fragment = ""

        # Render template
        jinja_env = Environment(
            loader=FileSystemLoader("data/templates"),
            autoescape=select_autoescape(["html", "xml"]),
        )
        template = jinja_env.get_template("article.html")
        rendered = template.render(
            content=html_fragment,
            authors=author_input,
            affiliations=converted_affiliations,
            title=converted_title,
            volume=pmeta["publication_info"]["pubvolume"],
            pdf_path=f"{doi.replace('/', '@')}.pdf",
            bib_path=f"{doi.replace('/', '@')}.bib",
            doi=doi,
            cite=cite,
            date=self.volume_meta["pubdate"],
            include_full_text=self.include_html,
            # Citation metadata
            cite_paper_url=cite_paper_url,
            cite_paper_title=converted_title,
            cite_date=self.volume_meta["pubyear"],
            cite_volume=pmeta["publication_info"]["pubvolume"],
            cit_first_page=pmeta["publication_info"]["pagestart"],
            cite_last_page=pmeta["publication_info"]["pageend"],
            cite_doi=doi,
            cite_authors=cite_authors,
            cite_editors=cite_editors,
            cite_abstract=abstract_text_clean,
            cite_language="en",
            cite_keywords=keywords_list,
            cite_html_url=cite_html_url,
            cite_pdf_url=cite_pdf_url,
        )

        html_path = self.output_dir / "index.html"
        html_path.write_text(rendered)
