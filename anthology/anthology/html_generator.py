"""HTML page generation for volume and table of contents pages."""

from pathlib import Path
from typing import List

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .utils import convert_latex_to_unicode
from .metadata import get_metadata


def make_volume_page(volume: str, papers: List) -> None:
    """
    Generate an index.html page for a specific volume.

    Creates a page listing all papers in the volume with their titles,
    authors, and page numbers.

    Args:
        volume: Volume directory name (e.g., "vol0001-2023-01-15")
        papers: List of Paper objects belonging to this volume

    Note:
        The generated HTML is written to docs/volumes/{volume}/index.html
        Uses the volume.html Jinja2 template from the templates directory
    """
    jinja_env = Environment(
        loader=FileSystemLoader("data/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = jinja_env.get_template("volume.html")

    # Extract paper data for the template
    paper_data = []
    for paper in papers:
        pmeta = paper.get_latex_metadata()
        doi = pmeta.get('publication_info').get('doi')
        paper_data.append({
            "title": convert_latex_to_unicode(pmeta["title"]),
            "authors": ", ".join([convert_latex_to_unicode(x['name']) for x in pmeta["authors"]]),
            "url": str(paper.output_dir.name),
            "pagestart": int(pmeta['publication_info']['pagestart']),
            "pageend": int(pmeta['publication_info']['pageend'])
        })

    # Get volume metadata from the first paper
    volume_meta = papers[0].volume_meta

    # Render the template
    rendered = template.render(
        papers=paper_data,
        date=volume_meta["date"],
        pubvolume=volume_meta["pubvolume"],
        conferencename=volume_meta.get("conferencename"),
        conferenceeditors=volume_meta.get("conferenceeditors"),
        description=volume_meta.get("description")
    )

    # Write to output directory
    html_path = Path("docs/volumes") / volume / "index.html"
    html_path.write_text(rendered)


def make_toc_page(all_papers: List) -> None:
    """
    Generate the main table of contents page listing all volumes.

    Creates the root index.html page that serves as an entry point
    to the anthology, listing all volumes with their metadata and
    paper counts.

    Args:
        all_papers: List of all Paper objects across all volumes

    Note:
        The generated HTML is written to docs/volumes/index.html
        Uses the toc.html Jinja2 template from the templates directory
    """
    jinja_env = Environment(
        loader=FileSystemLoader("data/templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = jinja_env.get_template("toc.html")

    # Get metadata for all volumes
    metadata = get_metadata()

    # Group papers by volume and count them
    volume_data = []
    # Sort volumes in reverse order (newest first)
    volumes = sorted(set([p.volume for p in all_papers]), reverse=True)

    for volume in volumes:
        volume_papers = [p for p in all_papers if p.volume == volume]
        volume_meta = metadata.get(volume, {})

        # Get conference name and editors, treating "—" as empty
        conferencename = volume_meta.get("conferencename", "")
        conferenceeditors = volume_meta.get("conferenceeditors", "")

        # Treat em dash as empty string
        if conferencename == "—":
            conferencename = ""
        if conferenceeditors == "—":
            conferenceeditors = ""

        volume_info = {
            "pubvolume": volume_meta.get("pubvolume", ""),
            "conferencename": conferencename,
            "date": volume_meta.get("date", ""),
            "conferenceeditors": conferenceeditors,
            "num_papers": len(volume_papers),
            "url": f"{volume}/"
        }
        volume_data.append(volume_info)

    # Render the template
    rendered = template.render(volumes=volume_data)

    # Write to output directory
    html_path = Path("docs/volumes") / "index.html"
    html_path.write_text(rendered)
