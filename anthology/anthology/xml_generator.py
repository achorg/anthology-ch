"""Crossref XML metadata generation for DOI registration."""

import re
import random
import string
from pathlib import Path
from typing import List
from datetime import datetime
from xml.etree import ElementTree as ET
from xml.dom import minidom

from .utils import convert_latex_to_unicode, strip_html_tags


def create_crossref_xml(volume: str, papers: List, verbose: bool = False) -> None:
    """
    Create a Crossref XML file for DOI registration.

    Generates an XML file conforming to the Crossref schema that contains
    metadata for all articles in a volume. This file can be submitted to
    Crossref to register DOIs for the papers.

    Args:
        volume: Volume directory name (e.g., "vol0001-2023-01-15")
        papers: List of Paper objects in this volume
        verbose: If True, print confirmation message (default: False)

    Note:
        The XML file is written to xml/crossref-{volume}.xml
        Schema version: Crossref 4.4.2
        Includes: titles, authors, ORCIDs, abstracts, publication dates, pages, DOIs
    """
    # Generate batch ID and timestamp
    batch_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=23))
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]  # milliseconds precision

    # Get volume metadata
    volume_meta = papers[0].volume_meta

    # Parse publication date from volume metadata
    pubdate = volume_meta.get("pubdate", "")
    # Extract month, day, year from pubdate (format: "DD Month YYYY")
    date_match = re.match(r'(\d+)\s+(\w+)\s+(\d{4})', pubdate)
    if date_match:
        day = date_match.group(1).zfill(2)
        month_name = date_match.group(2)
        year = date_match.group(3)
        # Convert month name to number
        months = {
            'January': '01', 'February': '02', 'March': '03', 'April': '04',
            'May': '05', 'June': '06', 'July': '07', 'August': '08',
            'September': '09', 'October': '10', 'November': '11', 'December': '12'
        }
        month = months.get(month_name, '01')
    else:
        # Fallback to year only
        day = '01'
        month = '01'
        year = volume_meta.get("pubyear", "2025")

    # Create root element with namespaces
    doi_batch = ET.Element('doi_batch', {
        'version': '4.4.2',
        'xmlns': 'http://www.crossref.org/schema/4.4.2',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xmlns:jats': 'http://www.ncbi.nlm.nih.gov/JATS1',
        'xsi:schemaLocation': 'http://www.crossref.org/schema/4.4.2 http://www.crossref.org/schema/deposit/crossref4.4.2.xsd'
    })

    # Head section
    head = ET.SubElement(doi_batch, 'head')
    ET.SubElement(head, 'doi_batch_id').text = batch_id
    ET.SubElement(head, 'timestamp').text = timestamp

    depositor = ET.SubElement(head, 'depositor')
    ET.SubElement(depositor, 'depositor_name').text = 'taylor@dvlab.org:4chu'
    ET.SubElement(depositor, 'email_address').text = 'tarnold2@richmond.edu'

    ET.SubElement(head, 'registrant').text = 'WEB-FORM'

    # Body section
    body = ET.SubElement(doi_batch, 'body')
    journal = ET.SubElement(body, 'journal')

    # Journal metadata
    journal_metadata = ET.SubElement(journal, 'journal_metadata')
    ET.SubElement(journal_metadata, 'full_title').text = 'Anthology of Computers and the Humanities'
    ET.SubElement(journal_metadata, 'abbrev_title').text = 'Anth. Comp. Hum.'

    journal_doi_data = ET.SubElement(journal_metadata, 'doi_data')
    ET.SubElement(journal_doi_data, 'doi').text = '10.63744/GJCCSMz4QBbD'
    ET.SubElement(journal_doi_data, 'resource').text = 'https://anthology.ach.org/'

    # Journal issue
    journal_issue = ET.SubElement(journal, 'journal_issue')
    pub_date_issue = ET.SubElement(journal_issue, 'publication_date', {'media_type': 'print'})
    ET.SubElement(pub_date_issue, 'month').text = month
    ET.SubElement(pub_date_issue, 'day').text = day
    ET.SubElement(pub_date_issue, 'year').text = year

    journal_volume = ET.SubElement(journal_issue, 'journal_volume')
    ET.SubElement(journal_volume, 'volume').text = volume_meta.get("pubvolume", "1")

    # Add articles
    for paper in papers:
        pmeta = paper.get_latex_metadata()
        doi = pmeta.get('publication_info', {}).get('doi', '')

        # Create journal_article element
        journal_article = ET.SubElement(journal, 'journal_article', {'publication_type': 'full_text'})

        # Titles
        titles = ET.SubElement(journal_article, 'titles')
        title_text = convert_latex_to_unicode(pmeta.get("title", ""))
        # Strip HTML tags from title if present
        title_text = strip_html_tags(title_text)
        ET.SubElement(titles, 'title').text = title_text

        # Contributors
        contributors = ET.SubElement(journal_article, 'contributors')
        for idx, author in enumerate(pmeta.get("authors", [])):
            sequence = 'first' if idx == 0 else 'additional'
            person_name = ET.SubElement(contributors, 'person_name', {
                'sequence': sequence,
                'contributor_role': 'author'
            })

            # Split author name into given_name and surname
            author_name = convert_latex_to_unicode(author.get("name", ""))
            name_parts = author_name.strip().split()
            if len(name_parts) > 1:
                given_name = " ".join(name_parts[:-1])
                surname = name_parts[-1]
            else:
                given_name = ""
                surname = name_parts[0] if name_parts else ""

            if given_name:
                ET.SubElement(person_name, 'given_name').text = given_name
            ET.SubElement(person_name, 'surname').text = surname

            # Add ORCID if present
            if 'orcid' in author.get('metadata', {}):
                orcid = author['metadata']['orcid']
                # Clean up ORCID - extract just the ID, remove any email or extra text
                orcid = orcid.split()[0]  # Take only the first part before any space
                # Ensure ORCID is in full URL format
                if not orcid.startswith('http'):
                    orcid = f'https://orcid.org/{orcid}'
                ET.SubElement(person_name, 'ORCID').text = orcid

        # Abstract
        abstract_text = pmeta.get("abstract", "")
        if abstract_text:
            abstract = ET.SubElement(journal_article, '{http://www.ncbi.nlm.nih.gov/JATS1}abstract', {'xml:lang': 'en'})
            abstract_p = ET.SubElement(abstract, '{http://www.ncbi.nlm.nih.gov/JATS1}p')
            # Clean up abstract text
            abstract_text = convert_latex_to_unicode(abstract_text)
            abstract_text = strip_html_tags(abstract_text)
            abstract_p.text = abstract_text

        # Publication date
        pub_date_article = ET.SubElement(journal_article, 'publication_date', {'media_type': 'print'})
        ET.SubElement(pub_date_article, 'month').text = month
        ET.SubElement(pub_date_article, 'day').text = day
        ET.SubElement(pub_date_article, 'year').text = year

        # Pages
        pages = ET.SubElement(journal_article, 'pages')
        ET.SubElement(pages, 'first_page').text = str(pmeta.get('publication_info', {}).get('pagestart', '1'))
        ET.SubElement(pages, 'last_page').text = str(pmeta.get('publication_info', {}).get('pageend', '1'))

        # DOI data
        article_doi_data = ET.SubElement(journal_article, 'doi_data')
        ET.SubElement(article_doi_data, 'doi').text = doi

        # Construct resource URL
        base_url = "https://anthology.ach.org"
        volume_path = f"vol{paper.volumeid:04d}"
        paper_slug = paper.output_dir.name
        resource_url = f"{base_url}/volumes/{volume_path}/{paper_slug}/"
        ET.SubElement(article_doi_data, 'resource').text = resource_url

    # Pretty print the XML
    xml_str = ET.tostring(doi_batch, encoding='unicode')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='UTF-8')

    # Remove extra blank lines
    lines = pretty_xml.decode('utf-8').split('\n')
    lines = [line for line in lines if line.strip()]
    pretty_xml = '\n'.join(lines)

    # Write to file
    output_path = Path("data/xml") / f"crossref-{volume}.xml"
    output_path.parent.mkdir(exist_ok=True)
    output_path.write_text(pretty_xml, encoding='utf-8')

    if verbose:
        print(f"Created Crossref XML: {output_path}")
