"""Sitemap and RSS feed generation for the anthology website."""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, register_namespace, tostring

from .utils import convert_latex_to_unicode, strip_html_tags


def create_sitemap(
    all_papers: List, output_path: Optional[Path] = None, verbose: bool = False
) -> None:
    """
    Generate a sitemap.xml file for the anthology website.

    Creates a standard XML sitemap containing URLs for:
    - Main index page
    - Volumes index page
    - Individual volume pages
    - Individual paper pages

    Args:
        all_papers: List of all Paper objects across all volumes
        output_path: Path where sitemap.xml should be written (default: docs/sitemap.xml)
        verbose: If True, print progress information
    """
    if output_path is None:
        output_path = Path("docs/sitemap.xml")

    base_url = "https://anthology.ach.org"

    # Create root element
    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    # Add main index page
    url_elem = SubElement(urlset, "url")
    SubElement(url_elem, "loc").text = f"{base_url}/"
    SubElement(url_elem, "changefreq").text = "monthly"
    SubElement(url_elem, "priority").text = "1.0"

    # Add volumes index page
    url_elem = SubElement(urlset, "url")
    SubElement(url_elem, "loc").text = f"{base_url}/volumes/"
    SubElement(url_elem, "changefreq").text = "monthly"
    SubElement(url_elem, "priority").text = "0.9"

    # Add about page
    url_elem = SubElement(urlset, "url")
    SubElement(url_elem, "loc").text = f"{base_url}/about/"
    SubElement(url_elem, "changefreq").text = "yearly"
    SubElement(url_elem, "priority").text = "0.7"

    # Group papers by volume
    volumes = sorted(set([p.volume for p in all_papers]))

    # Add volume pages
    for volume in volumes:
        volume_papers = [p for p in all_papers if p.volume == volume]
        volume_num = volume_papers[0].volumeid

        url_elem = SubElement(urlset, "url")
        SubElement(url_elem, "loc").text = f"{base_url}/volumes/vol{volume_num:04d}/"
        SubElement(url_elem, "changefreq").text = "yearly"
        SubElement(url_elem, "priority").text = "0.8"

        # Get publication date if available
        if "pubdate" in volume_papers[0].volume_meta:
            pubdate = volume_papers[0].volume_meta["pubdate"]
            SubElement(url_elem, "lastmod").text = pubdate

    # Add paper pages
    for paper in all_papers:
        volume_num = paper.volumeid
        paper_slug = paper.output_dir.name

        url_elem = SubElement(urlset, "url")
        SubElement(
            url_elem, "loc"
        ).text = f"{base_url}/volumes/vol{volume_num:04d}/{paper_slug}/"
        SubElement(url_elem, "changefreq").text = "yearly"
        SubElement(url_elem, "priority").text = "0.6"

        # Add publication date if available
        if "pubdate" in paper.volume_meta:
            pubdate = paper.volume_meta["pubdate"]
            SubElement(url_elem, "lastmod").text = pubdate

    # Pretty print XML
    xml_str = minidom.parseString(tostring(urlset, encoding="unicode")).toprettyxml(
        indent="  "
    )

    # Remove extra blank lines
    xml_lines = [line for line in xml_str.split("\n") if line.strip()]
    xml_str = "\n".join(xml_lines) + "\n"

    # Write to file
    output_path.write_text(xml_str, encoding="utf-8")

    if verbose:
        print(f"Sitemap written to {output_path}")
        print(f"  Total URLs: {len(urlset.findall('url'))}")


def create_rss_feed(
    all_papers: List, output_path: Optional[Path] = None, verbose: bool = False
) -> None:
    """
    Generate an RSS 2.0 feed for the anthology website.

    Creates an RSS feed containing all papers, with most recent papers first.
    Each item includes title, authors, abstract, publication date, and link.

    Args:
        all_papers: List of all Paper objects across all volumes
        output_path: Path where rss.xml should be written (default: docs/rss.xml)
        verbose: If True, print progress information
    """
    if output_path is None:
        output_path = Path("docs/rss.xml")

    base_url = "https://anthology.ach.org"

    # Register namespaces for cleaner output
    register_namespace("atom", "http://www.w3.org/2005/Atom")
    register_namespace("dc", "http://purl.org/dc/elements/1.1/")

    # Create root element
    rss = Element("rss")
    rss.set("version", "2.0")

    channel = SubElement(rss, "channel")

    # Channel metadata
    SubElement(channel, "title").text = "Anthology for Computers and the Humanities"
    SubElement(channel, "link").text = base_url
    SubElement(channel, "description").text = (
        "Anthology for Computers and the Humanities (ACH) is an open-access journal "
        "publishing technical papers, software documentation, and research in digital humanities."
    )
    SubElement(channel, "language").text = "en"
    SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    # Add atom:link for self-reference
    atom_link = SubElement(channel, "{http://www.w3.org/2005/Atom}link")
    atom_link.set("href", f"{base_url}/rss.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # Sort papers by volume and paper order (most recent first)
    sorted_papers = sorted(
        all_papers, key=lambda p: (p.volumeid, p.paper_order), reverse=True
    )

    # Add items for each paper
    for paper in sorted_papers:
        pmeta = paper.get_latex_metadata()
        volume_num = paper.volumeid
        paper_slug = paper.output_dir.name

        item = SubElement(channel, "item")

        # Title
        title = convert_latex_to_unicode(pmeta["title"])
        SubElement(item, "title").text = title

        # Link
        paper_url = f"{base_url}/volumes/vol{volume_num:04d}/{paper_slug}/"
        SubElement(item, "link").text = paper_url
        SubElement(item, "guid").text = paper_url

        # Authors
        authors = [convert_latex_to_unicode(a["name"]) for a in pmeta["authors"]]
        for author in authors:
            SubElement(item, "{http://purl.org/dc/elements/1.1/}creator").text = author

        # Description (abstract)
        if "abstract" in pmeta and pmeta["abstract"]:
            abstract = convert_latex_to_unicode(pmeta["abstract"])
            # Remove any HTML tags if present
            abstract_clean = strip_html_tags(abstract)
            SubElement(item, "description").text = abstract_clean

        # Publication date
        if "pubdate" in paper.volume_meta:
            try:
                # Parse date and convert to RFC 822 format
                pub_date = datetime.strptime(paper.volume_meta["pubdate"], "%Y-%m-%d")
                pub_date_str = pub_date.strftime("%a, %d %b %Y 00:00:00 +0000")
                SubElement(item, "pubDate").text = pub_date_str
            except ValueError:
                # If date parsing fails, skip it
                pass

        # DOI
        if "publication_info" in pmeta and "doi" in pmeta["publication_info"]:
            doi = pmeta["publication_info"]["doi"]
            SubElement(
                item, "{http://purl.org/dc/elements/1.1/}identifier"
            ).text = f"https://doi.org/{doi}"

    # Pretty print XML
    xml_str = minidom.parseString(tostring(rss, encoding="unicode")).toprettyxml(
        indent="  "
    )

    # Remove extra blank lines
    xml_lines = [line for line in xml_str.split("\n") if line.strip()]
    xml_str = "\n".join(xml_lines) + "\n"

    # Write to file
    output_path.write_text(xml_str, encoding="utf-8")

    if verbose:
        print(f"RSS feed written to {output_path}")
        print(f"  Total items: {len(channel.findall('item'))}")
