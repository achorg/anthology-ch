"""Command-line interface for the ACH Anthology journal processor."""

from pathlib import Path

import click

from . import __version__
from .html_generator import make_toc_page, make_volume_page
from .metadata import discover_output_papers, get_all_papers
from .sitemap_generator import create_rss_feed, create_sitemap
from .xml_generator import create_crossref_xml


def update_paper_ordering(papers, verbose=False):
    """
    Update paper ordering in LaTeX files and metadata.

    This function recalculates paper order numbers based on the current
    sorting of papers (by volumeid and paperid) and updates both the
    LaTeX files (\\paperorder{}) and anthology-meta.json files.

    This is called during both the prepare and build phases to ensure
    paper ordering stays synchronized even if papers are reordered.

    Args:
        papers: List of Paper objects (must be sorted)
        verbose: Whether to print detailed output

    Note:
        Paper order is reset to 1 for each new volume.
    """
    cur_volume = 0
    paper_order = 1

    for p in papers:
        # Reset paper order for each volume
        if cur_volume != p.volumeid:
            paper_order = 1
            cur_volume = p.volumeid

        # Update the paper's order
        p.update_paper_order(paper_order, verbose=verbose)
        paper_order += 1


@click.group()
@click.version_option(version=__version__)
def cli():
    """ACH Anthology journal processor CLI.

    A tool for processing journal articles from LaTeX sources to
    generate PDFs, HTML, BibTeX citations, and Crossref XML metadata.
    """
    pass


@cli.command("doi-add")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def doi_add(verbose):
    """Add DOIs to papers that have placeholder DOIs."""
    papers = get_all_papers()

    if verbose:
        click.echo(f"Found {len(papers)} papers")

    for paper in papers:
        if verbose:
            click.echo(f"Processing: {paper.output_dir.name}")
        paper.add_doi(verbose=verbose)

    click.echo("✓ DOI addition complete")


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option(
    "--volume", type=str, help="Prepare only a specific volume (e.g., 'vol0001' or '1')"
)
def prepare(verbose, volume):
    """Phase 1: Copy input files to output directory and prepare for building.

    This command:
    - Adds DOIs to papers with placeholders
    - Copies LaTeX files, bibliographies, and figures to output directory
    - Sets paper order numbers
    - Saves metadata for input-independent building

    After this step, papers can be built without access to the input directory.
    """
    click.echo("Phase 1: Preparing papers (copying input to output)...")
    click.echo()

    papers = get_all_papers()

    # Filter by volume if specified
    if volume:
        # Normalize volume name (accept 'vol0001', '0001', or '1')
        if not volume.startswith("vol"):
            volume_num = int(volume)
            volume = f"vol{volume_num:04d}"

        # Filter papers by volume
        papers = [p for p in papers if p.volume.startswith(volume)]

        if not papers:
            click.echo(f"✗ No papers found for volume {volume}!", err=True)
            raise click.Abort()

        click.echo(f"Preparing volume: {volume}")
        click.echo(f"Found {len(papers)} papers")
    else:
        click.echo(f"Found {len(papers)} papers")

    click.echo()

    # Step 1: Add DOIs
    click.echo("Step 1: Adding DOIs...")
    for p in papers:
        p.add_doi(verbose=verbose)
    click.echo("✓ DOI addition complete")
    click.echo()

    # Step 2: Copy files to output with proper ordering
    click.echo("Step 2: Copying files to output...")
    cur_volume = 0
    paper_order = 1

    for p in papers:
        # Reset paper order for each volume
        if cur_volume != p.volumeid:
            paper_order = 1
            cur_volume = p.volumeid

        if verbose:
            click.echo(f"  Copying: {p.output_dir.name} (order: {paper_order})")
        else:
            click.echo(f"  Copying: {p.output_dir.name}", nl=False)

        p.copy_to_output(verbose=verbose, order=paper_order)
        paper_order += 1

        if not verbose:
            click.echo(" ✓")

    click.echo()
    click.echo("=" * 50)
    click.echo("✓ Preparation complete!")
    click.echo("=" * 50)
    click.echo()
    click.echo("Next step: Run 'anthology build' to compile and generate outputs")


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show LaTeX compilation output")
@click.option(
    "--paper",
    type=click.Path(exists=True, path_type=Path),
    help="Compile specific paper directory",
)
def compile(verbose, paper):
    """Compile papers to PDF using XeLaTeX."""
    if paper:
        # Compile specific paper
        from .paper import Paper

        # Load paper from output directory metadata
        p = Paper.from_output_dir(paper)
        if not p:
            click.echo(f"Error: Could not load paper from {paper}", err=True)
            click.echo(
                "Make sure the paper has been prepared first with 'anthology prepare'",
                err=True,
            )
            raise click.Abort()

        click.echo(f"Compiling: {p.output_dir.name}")

        # Clean auxiliary files before compilation
        p.clean_xelatex()

        success = p.compile_xelatex(verbose=verbose)

        if success:
            click.echo("✓ Compilation successful")
        else:
            click.echo("✗ Compilation failed", err=True)
            raise click.Abort()
    else:
        # Compile all papers
        papers = get_all_papers()

        if verbose:
            click.echo(f"Found {len(papers)} papers")

        failed = []
        cur_volume = 0
        paper_order = 1

        for paper in papers:
            # Reset paper order for each volume
            if cur_volume != paper.volumeid:
                paper_order = 1
                cur_volume = paper.volumeid

            if verbose:
                click.echo(f"Compiling: {paper.output_dir.name}")
            else:
                click.echo(f"Compiling: {paper.output_dir.name}", nl=False)

            paper.copy_to_output(verbose=verbose, order=paper_order)

            # Clean auxiliary files before compilation
            paper.clean_xelatex()

            success = paper.compile_xelatex(verbose=verbose)

            if success:
                if not verbose:
                    click.echo(" ✓")
            else:
                if not verbose:
                    click.echo(" ✗")
                failed.append(paper.output_dir.name)

            # Increment order regardless of success (order is based on position)
            paper_order += 1

        if failed:
            click.echo(f"\n✗ {len(failed)} paper(s) failed to compile:", err=True)
            for name in failed:
                click.echo(f"  - {name}", err=True)
            raise click.Abort()
        else:
            click.echo("\n✓ All papers compiled successfully")


@cli.group()
def generate():
    """Generate various outputs (HTML, BibTeX, XML, etc.)."""
    pass


@generate.command("html")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
@click.option(
    "--paper",
    type=click.Path(exists=True, path_type=Path),
    help="Generate HTML for a specific paper directory",
)
@click.option(
    "--volume", type=str, help="Generate HTML for a specific volume (e.g., 'vol0001' or '1')"
)
def generate_html(verbose, paper, volume):
    """Generate HTML versions of papers.

    If --paper is specified, generates HTML for that paper only.
    If --volume is specified, generates HTML for all papers in that volume.
    Otherwise, generates HTML for all papers.
    """
    if paper and volume:
        click.echo("Error: Cannot specify both --paper and --volume", err=True)
        raise click.Abort()

    if paper:
        # Generate HTML for specific paper
        from .paper import Paper

        # Load paper from output directory metadata
        p = Paper.from_output_dir(paper)
        if not p:
            click.echo(f"Error: Could not load paper from {paper}", err=True)
            click.echo(
                "Make sure the paper has been prepared first with 'anthology prepare'",
                err=True,
            )
            raise click.Abort()

        click.echo(f"Generating HTML: {p.output_dir.name}")
        try:
            p.create_html(verbose=verbose)
            click.echo("✓ HTML generation complete")
        except Exception as e:
            click.echo(f"✗ HTML generation failed: {e}", err=True)
            raise click.Abort()
    else:
        # Generate HTML for all papers (or filtered by volume)
        papers = discover_output_papers()

        if not papers:
            click.echo("✗ No papers found in output directory!", err=True)
            click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
            raise click.Abort()

        # Filter by volume if specified
        if volume:
            # Normalize volume name (accept 'vol0001', '0001', or '1')
            if not volume.startswith("vol"):
                volume_num = int(volume)
                volume = f"vol{volume_num:04d}"

            # Filter papers by volume
            papers = [p for p in papers if p.volume.startswith(volume)]

            if not papers:
                click.echo(f"✗ No papers found for volume {volume}!", err=True)
                raise click.Abort()

            if verbose:
                click.echo(f"Generating HTML for {len(papers)} papers in {volume}")
            else:
                click.echo(f"Generating HTML for volume {volume}")
        elif verbose:
            click.echo(f"Generating HTML for {len(papers)} papers")

        html_failed = []
        for p in papers:
            if verbose:
                click.echo(f"Processing: {p.output_dir.name}")
            else:
                click.echo(f"Processing: {p.output_dir.name}", nl=False)

            try:
                p.create_html(verbose=verbose)
                if not verbose:
                    click.echo(" ✓")
            except Exception as e:
                if not verbose:
                    click.echo(" ✗")
                click.echo(f"  Warning: HTML generation failed for {p.output_dir.name}: {e}", err=True)
                html_failed.append(p.output_dir.name)

        if html_failed:
            click.echo(f"\n⚠ {len(html_failed)} paper(s) failed HTML generation:", err=True)
            for name in html_failed:
                click.echo(f"  - {name}", err=True)
            click.echo("✓ HTML generation complete (with warnings)")
        else:
            click.echo("✓ HTML generation complete")


@generate.command("pdf")
@click.option("--verbose", "-v", is_flag=True, help="Show LaTeX compilation output")
@click.option(
    "--paper",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Paper directory to compile to PDF",
)
@click.option(
    "--pages",
    type=str,
    help="Page range for metadata (e.g., '1-10'). If not provided, PDF will be compiled without page metadata.",
)
def generate_pdf(verbose, paper, pages):
    """Generate PDF for a specific paper.

    This command compiles a single paper to PDF using XeLaTeX. Optionally,
    you can specify page numbers to include in the metadata.

    Examples:
        anthology generate pdf --paper docs/volumes/vol0001/paper-slug/
        anthology generate pdf --paper docs/volumes/vol0001/paper-slug/ --pages 1-15
    """
    from .paper import Paper

    # Load paper from output directory metadata
    p = Paper.from_output_dir(paper)
    if not p:
        click.echo(f"Error: Could not load paper from {paper}", err=True)
        click.echo(
            "Make sure the paper has been prepared first with 'anthology prepare'",
            err=True,
        )
        raise click.Abort()

    click.echo(f"Generating PDF: {p.output_dir.name}")

    # Clean auxiliary files before compilation
    p.clean_xelatex()

    # First compilation
    click.echo("  Compiling with XeLaTeX (pass 1)...")
    success = p.compile_xelatex(verbose=verbose)
    if not success:
        click.echo("✗ Compilation failed", err=True)
        raise click.Abort()

    # If pages are specified, add metadata and recompile
    if pages:
        try:
            page_parts = pages.split("-")
            if len(page_parts) != 2:
                click.echo(
                    "Error: Page range must be in format 'start-end' (e.g., '1-10')",
                    err=True,
                )
                raise click.Abort()

            page_start = int(page_parts[0])
            page_end = int(page_parts[1])

            if page_start > page_end:
                click.echo("Error: Start page must be <= end page", err=True)
                raise click.Abort()

            click.echo(f"  Adding metadata (pages {page_start}-{page_end})...")
            p.add_metadata(page_start, page_end)

            click.echo("  Recompiling with metadata (pass 2)...")
            success = p.compile_xelatex(verbose=verbose)
            if not success:
                click.echo("✗ Recompilation failed", err=True)
                raise click.Abort()

        except ValueError as e:
            click.echo(f"Error: Invalid page range '{pages}': {e}", err=True)
            raise click.Abort()

    # Clean auxiliary files
    p.clean_xelatex()

    # Rename PDF to DOI-based filename
    p.move_pdf()

    # Add metadata to PDF
    p.add_pdf_metadata()

    # Report final location
    pmeta = p.get_latex_metadata()
    doi = pmeta.get("publication_info", {}).get("doi", "")
    pdf_path = p.output_dir / f"{doi.replace('/', '@')}.pdf"
    click.echo(f"✓ PDF generated: {pdf_path}")


@generate.command("bibtex")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def generate_bibtex(verbose):
    """Generate BibTeX citation files for all papers."""
    papers = discover_output_papers()

    if not papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    if verbose:
        click.echo(f"Generating BibTeX for {len(papers)} papers")

    for paper in papers:
        if verbose:
            click.echo(f"Generating: {paper.output_dir.name}")
        paper.create_bibtex()

    click.echo("✓ BibTeX generation complete")


@generate.command("volumes")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def generate_volumes(verbose):
    """Generate volume index pages."""
    papers = discover_output_papers()

    if not papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    volumes = list(set([x.volume for x in papers]))

    if verbose:
        click.echo(f"Generating volume pages for {len(volumes)} volumes")

    for vol in volumes:
        if verbose:
            click.echo(f"Generating: {vol}")
        papers_vol = [x for x in papers if x.volume == vol]
        make_volume_page(vol, papers_vol)

    click.echo("✓ Volume page generation complete")


@generate.command("toc")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def generate_toc(verbose):
    """Generate the main table of contents page."""
    papers = discover_output_papers()

    if not papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    if verbose:
        click.echo("Generating main table of contents")

    make_toc_page(papers)

    click.echo("✓ Table of contents generation complete")


@generate.command("xml")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def generate_xml(verbose):
    """Generate Crossref XML metadata files."""
    papers = discover_output_papers()

    if not papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    volumes = list(set([x.volume for x in papers]))

    if verbose:
        click.echo(f"Generating Crossref XML for {len(volumes)} volumes")

    for vol in volumes:
        papers_vol = [x for x in papers if x.volume == vol]
        create_crossref_xml(vol, papers_vol, verbose=verbose)

    if not verbose:
        click.echo("✓ Crossref XML generation complete")


@generate.command("sitemap")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def generate_sitemap(verbose):
    """Generate sitemap.xml for the website."""
    papers = discover_output_papers()

    if not papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    if verbose:
        click.echo("Generating sitemap.xml")

    create_sitemap(papers, verbose=verbose)
    click.echo("✓ Sitemap generation complete")


@generate.command("rss")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def generate_rss(verbose):
    """Generate RSS feed for the website."""
    papers = discover_output_papers()

    if not papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    if verbose:
        click.echo("Generating rss.xml")

    create_rss_feed(papers, verbose=verbose)
    click.echo("✓ RSS feed generation complete")


@generate.command("all")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def generate_all(verbose):
    """Generate all outputs (HTML, BibTeX, volumes, TOC, XML, sitemap, RSS)."""
    click.echo("Generating all outputs...")

    papers = discover_output_papers()

    if not papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    # Generate HTML
    if verbose:
        click.echo(f"\nGenerating HTML for {len(papers)} papers")
    html_failed = []
    for paper in papers:
        if verbose:
            click.echo(f"Processing: {paper.output_dir.name}")
        else:
            click.echo(f"Processing: {paper.output_dir.name}", nl=False)

        try:
            paper.create_html(verbose=verbose)
            if not verbose:
                click.echo(" ✓")
        except Exception as e:
            if not verbose:
                click.echo(" ✗")
            click.echo(f"  Warning: HTML generation failed for {paper.output_dir.name}: {e}", err=True)
            html_failed.append(paper.output_dir.name)

    if html_failed:
        click.echo(f"\n⚠ {len(html_failed)} paper(s) failed HTML generation:", err=True)
        for name in html_failed:
            click.echo(f"  - {name}", err=True)
        click.echo("✓ HTML generation complete (with warnings)")
    else:
        click.echo("✓ HTML generation complete")

    # Generate BibTeX
    if verbose:
        click.echo(f"\nGenerating BibTeX for {len(papers)} papers")
    for paper in papers:
        if verbose:
            click.echo(f"  BibTeX: {paper.output_dir.name}")
        paper.create_bibtex()
    click.echo("✓ BibTeX generation complete")

    # Generate volume pages
    volumes = list(set([x.volume for x in papers]))
    if verbose:
        click.echo(f"\nGenerating volume pages for {len(volumes)} volumes")
    for vol in volumes:
        if verbose:
            click.echo(f"  Volume: {vol}")
        papers_vol = [x for x in papers if x.volume == vol]
        make_volume_page(vol, papers_vol)
    click.echo("✓ Volume page generation complete")

    # Generate TOC
    if verbose:
        click.echo("\nGenerating main table of contents")
    make_toc_page(papers)
    click.echo("✓ Table of contents generation complete")

    # Generate Crossref XML
    if verbose:
        click.echo(f"\nGenerating Crossref XML for {len(volumes)} volumes")
    for vol in volumes:
        papers_vol = [x for x in papers if x.volume == vol]
        create_crossref_xml(vol, papers_vol, verbose=verbose)
    if not verbose:
        click.echo("✓ Crossref XML generation complete")

    # Generate sitemap
    if verbose:
        click.echo("\nGenerating sitemap")
    create_sitemap(papers, verbose=verbose)
    click.echo("✓ Sitemap generation complete")

    # Generate RSS feed
    if verbose:
        click.echo("\nGenerating RSS feed")
    create_rss_feed(papers, verbose=verbose)
    click.echo("✓ RSS feed generation complete")

    click.echo("\n✓ All generation complete")


@cli.command()
@click.option(
    "--verbose", "-v", is_flag=True, help="Show detailed output and LaTeX errors"
)
@click.option(
    "--volume", type=str, help="Build only a specific volume (e.g., 'vol0001' or '1')"
)
def build(verbose, volume):
    """Phase 2: Build papers from output directory (compile, generate HTML, etc.).

    This command works entirely from the output directory and does not require
    access to the input directory. Run 'anthology prepare' first to copy files
    from input to output.

    Steps:
    1. Discover papers in output directory
    2. Update paper ordering in LaTeX files and metadata
    3. Compile papers with XeLaTeX
    4. Add metadata (page numbers, volume info)
    5. Recompile with final metadata
    6. Clean auxiliary files
    7. Rename PDFs
    8. Generate BibTeX, HTML, volume pages, Crossref XML, sitemap, RSS feed, and TOC
    """
    click.echo("Phase 2: Building papers from output directory...")
    click.echo()

    # Discover papers from output directory
    all_papers = discover_output_papers()

    if not all_papers:
        click.echo("✗ No papers found in output directory!", err=True)
        click.echo("Run 'anthology prepare' first to copy files from input/", err=True)
        raise click.Abort()

    # Filter by volume if specified (for compilation/generation)
    # But keep all_papers for sitemap, RSS, and TOC
    if volume:
        # Normalize volume name (accept 'vol0001', '0001', or '1')
        if not volume.startswith("vol"):
            volume_num = int(volume)
            volume = f"vol{volume_num:04d}"

        # Filter papers by volume for building
        papers = [p for p in all_papers if p.volume.startswith(volume)]

        if not papers:
            click.echo(f"✗ No papers found for volume {volume}!", err=True)
            raise click.Abort()

        click.echo(f"Building volume: {volume}")
        click.echo(f"Found {len(papers)} papers in {volume}")
        click.echo(f"(Sitemap, RSS, and TOC will include all {len(all_papers)} papers)")
    else:
        papers = all_papers
        click.echo(f"Found {len(papers)} papers in docs/volumes/")

    click.echo()

    # Update paper ordering before compilation
    click.echo("Step 1: Updating paper ordering...")
    update_paper_ordering(papers, verbose=verbose)
    click.echo("✓ Paper ordering updated")
    click.echo()

    # Compile and add metadata
    click.echo("Step 2: Compiling papers and adding metadata...")
    page_start = 1
    cur_volume = 0
    failed_papers = []

    for p in papers:
        # Reset page numbering for each volume
        if cur_volume != p.volumeid:
            page_start = 1
            cur_volume = p.volumeid

        if verbose:
            click.echo(f"\nProcessing: {p}")
        else:
            click.echo(f"Processing: {p.output_dir.name}", nl=False)

        # Clean auxiliary files before compilation
        p.clean_xelatex()

        # First compilation
        success = p.compile_xelatex(verbose=verbose)
        if not success:
            if not verbose:
                click.echo(" ✗ (compilation failed)")
            failed_papers.append(p.output_dir.name)
            continue

        # Get page count
        np = p.num_pages()

        # Check if volume is frozen
        is_frozen = p.volume_meta.get("frozen", False)

        if is_frozen:
            # For frozen volumes, read existing page numbers from the TeX file
            pmeta = p.get_latex_metadata()
            existing_start = pmeta.get("publication_info", {}).get("pagestart")
            existing_end = pmeta.get("publication_info", {}).get("pageend")

            if existing_start and existing_end:
                # Use existing page numbers (add_metadata will skip updating them)
                p.add_metadata(int(existing_start), int(existing_end))
                # Update page_start for next paper based on actual page count
                page_start = int(existing_end) + 1
                if verbose:
                    click.echo(f"  Volume frozen: keeping existing pages {existing_start}-{existing_end}")
            else:
                # No existing page numbers, treat as unfrozen
                if verbose:
                    click.echo(f"  Warning: Volume marked as frozen but no existing page numbers found")
                p.add_metadata(page_start, page_start + np - 1)
                page_start = page_start + np
        else:
            # Add metadata with calculated page numbers
            p.add_metadata(page_start, page_start + np - 1)
            page_start = page_start + np

        # Second compilation with metadata
        success = p.compile_xelatex(verbose=verbose)
        if not success:
            if not verbose:
                click.echo(" ✗ (recompilation failed)")
            failed_papers.append(p.output_dir.name)
            continue

        # Clean auxiliary files
        p.clean_xelatex()

        # Rename PDF
        p.move_pdf()

        # Add metadata to PDF
        p.add_pdf_metadata()

        if not verbose:
            click.echo(" ✓")

    if failed_papers:
        click.echo(f"\n✗ {len(failed_papers)} paper(s) failed:", err=True)
        for name in failed_papers:
            click.echo(f"  - {name}", err=True)
        click.echo("\nContinuing with successful papers...")
        # Filter out failed papers
        papers = [p for p in papers if p.output_dir.name not in failed_papers]
    else:
        click.echo("\n✓ All papers compiled successfully")

    click.echo()

    # Step 6: Generate BibTeX
    click.echo("Step 3: Generating BibTeX citations...")
    for p in papers:
        if verbose:
            click.echo(f"  {p.output_dir.name}")
        p.create_bibtex()
    click.echo("✓ BibTeX generation complete")
    click.echo()

    # Step 7: Generate HTML
    click.echo("Step 4: Generating HTML...")
    html_failed = []
    for p in papers:
        if verbose:
            click.echo(f"Processing: {p.output_dir.name}")
        else:
            click.echo(f"Processing: {p.output_dir.name}", nl=False)

        try:
            p.create_html(verbose=verbose)
            if not verbose:
                click.echo(" ✓")
        except Exception as e:
            if not verbose:
                click.echo(" ✗")
            click.echo(f"  Warning: HTML generation failed for {p.output_dir.name}: {e}", err=True)
            html_failed.append(p.output_dir.name)

    if html_failed:
        click.echo(f"\n⚠ {len(html_failed)} paper(s) failed HTML generation:", err=True)
        for name in html_failed:
            click.echo(f"  - {name}", err=True)
        click.echo("✓ HTML generation complete (with warnings)")
    else:
        click.echo("✓ HTML generation complete")
    click.echo()

    # Step 8: Generate volume pages
    click.echo("Step 5: Generating volume pages...")
    volumes = list(set([x.volume for x in papers]))
    for vol in volumes:
        if verbose:
            click.echo(f"  {vol}")
        papers_vol = [x for x in papers if x.volume == vol]
        make_volume_page(vol, papers_vol)
    click.echo("✓ Volume pages complete")
    click.echo()

    # Step 9: Generate Crossref XML
    click.echo("Step 6: Generating Crossref XML...")
    for vol in volumes:
        papers_vol = [x for x in papers if x.volume == vol]
        create_crossref_xml(vol, papers_vol, verbose=verbose)
    if not verbose:
        click.echo("✓ Crossref XML complete")
    click.echo()

    # Step 10: Generate sitemap (always use all papers)
    click.echo("Step 7: Generating sitemap...")
    create_sitemap(all_papers, verbose=verbose)
    click.echo("✓ Sitemap complete")
    click.echo()

    # Step 11: Generate RSS feed (always use all papers)
    click.echo("Step 8: Generating RSS feed...")
    create_rss_feed(all_papers, verbose=verbose)
    click.echo("✓ RSS feed complete")
    click.echo()

    # Step 12: Generate TOC (always use all papers)
    click.echo("Step 9: Generating table of contents...")
    make_toc_page(all_papers)
    click.echo("✓ Table of contents complete")
    click.echo()

    click.echo("=" * 50)
    click.echo("✓ Build pipeline complete!")
    click.echo("=" * 50)


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def clean(verbose):
    """Clean LaTeX auxiliary files from all output directories."""
    papers = get_all_papers()

    if verbose:
        click.echo(f"Cleaning {len(papers)} paper directories")

    for paper in papers:
        if verbose:
            click.echo(f"Cleaning: {paper.output_dir.name}")
        paper.clean_xelatex()

    click.echo("✓ Cleanup complete")


@cli.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed output")
def validate(verbose):
    """Validate that required input files exist for all papers."""
    papers = get_all_papers()

    if verbose:
        click.echo(f"Validating {len(papers)} papers")

    errors = []
    for paper in papers:
        try:
            paper.validate_input()
            if verbose:
                click.echo(f"✓ {paper.input_dir}")
        except FileNotFoundError as e:
            errors.append(str(e))
            click.echo(f"✗ {paper.input_dir}: {e}", err=True)

    if errors:
        click.echo(f"\n✗ Validation failed: {len(errors)} error(s)", err=True)
        raise click.Abort()
    else:
        click.echo("✓ All papers validated successfully")


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
