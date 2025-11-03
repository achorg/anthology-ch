"""Metadata management and paper discovery for the anthology journal processor."""

import json
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .paper import Paper


def get_metadata() -> Dict[str, Dict]:
    """
    Load volume metadata from data/metadata.json.

    Returns:
        Dictionary mapping volume names to their metadata.
        Each volume's metadata includes fields like:
        - pubvolume: Published volume number
        - pubyear: Publication year
        - pubdate: Full publication date
        - conferencename: Conference name
        - conferenceeditors: Conference editors
        - date: Display date
        - description: Volume description

    Raises:
        FileNotFoundError: If data/metadata.json doesn't exist
        json.JSONDecodeError: If the JSON file is malformed
    """
    metadata_path = Path("data/metadata.json")
    return json.loads(metadata_path.read_text())


def get_all_papers() -> List["Paper"]:
    """
    Discover all paper directories in the input folder.

    Scans the input/ directory for volume directories, then finds
    all paper directories within each volume. Creates Paper objects
    for each discovered paper.

    Returns:
        List of Paper objects, sorted by volume ID and paper ID

    Note:
        This function imports Paper locally to avoid circular imports.
        Expected directory structure:
        - input/
          - vol0001-YYYY-MM-DD/
            - paper001/
            - paper002/
          - vol0002-YYYY-MM-DD/
            - paper001/
    """
    # Local import to avoid circular dependency
    from .paper import Paper

    meta = get_metadata()

    volumes = [x for x in Path("input").glob("*") if x.is_dir()]
    papers = []

    for volume in volumes:
        paper_dirs = [x for x in volume.glob("*") if x.is_dir()]
        paper_objects = [Paper(x, meta[x.parent.name]) for x in paper_dirs]
        papers.extend(paper_objects)

    return sorted(papers)


def save_paper_metadata(
    output_dir: Path,
    input_dir: Path,
    paperid: int,
    volumeid: int,
    volume: str,
    volume_meta: Dict,
    paper_order: int,
    include_html: bool = True
) -> None:
    """
    Save paper metadata to the output directory.

    Creates an anthology-meta.json file containing all necessary information
    to rebuild the paper without access to the input directory.

    Args:
        output_dir: Output directory for this paper
        input_dir: Original input directory (saved for reference)
        paperid: Paper ID number
        volumeid: Volume ID number
        volume: Volume directory name
        volume_meta: Volume metadata dictionary
        paper_order: Paper order within the volume
        include_html: Whether to include full article text in HTML (default: True)
    """
    metadata = {
        "input_dir": str(input_dir),
        "paperid": paperid,
        "volumeid": volumeid,
        "volume": volume,
        "volume_meta": volume_meta,
        "paper_order": paper_order,
        "include_html": include_html
    }

    meta_file = output_dir / "anthology-meta.json"
    meta_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def load_paper_metadata(output_dir: Path) -> Optional[Dict]:
    """
    Load paper metadata from the output directory.

    Args:
        output_dir: Output directory containing anthology-meta.json

    Returns:
        Dictionary containing paper metadata, or None if not found
    """
    meta_file = output_dir / "anthology-meta.json"
    if not meta_file.exists():
        return None

    return json.loads(meta_file.read_text(encoding="utf-8"))


def discover_output_papers() -> List["Paper"]:
    """
    Discover all papers in the output directory.

    Scans the docs/volumes/ directory for paper directories containing
    an anthology-meta.json files and creates Paper objects from the
    saved metadata. This allows rebuilding without access to input/.

    Returns:
        List of Paper objects, sorted by volume ID and paper ID

    Note:
        Expected directory structure:
        - docs/volumes/
          - vol0001-YYYY-MM-DD/
            - paper-slug-1/
              - .anthology-meta.json
            - paper-slug-2/
              - .anthology-meta.json
    """
    # Local import to avoid circular dependency
    from .paper import Paper

    output_path = Path("docs/volumes")
    if not output_path.exists():
        return []

    papers = []

    # Find all volume directories
    volume_dirs = [x for x in output_path.glob("*") if x.is_dir()]

    for volume_dir in volume_dirs:
        # Find all paper directories in this volume
        paper_dirs = [x for x in volume_dir.glob("*") if x.is_dir()]

        for paper_dir in paper_dirs:
            meta_file = paper_dir / "anthology-meta.json"
            if meta_file.exists():
                # Create Paper from output directory
                paper = Paper.from_output_dir(paper_dir)
                if paper:
                    papers.append(paper)

    return sorted(papers)
