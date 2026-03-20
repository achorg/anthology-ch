#!/usr/bin/env python3
"""Validate CrossRef XML deposits against the local schema."""

import re
import sys
from pathlib import Path
from lxml import etree

SCHEMA_DIR = Path(__file__).parent / "schema"
XML_DIR = Path(__file__).parent / "xml"


def load_schema():
    parser = etree.XMLParser(load_dtd=False)
    schema_doc = etree.parse(SCHEMA_DIR / "crossref4.4.2.xsd", parser)
    return etree.XMLSchema(schema_doc)


def validate(files: list[Path], schema: etree.XMLSchema) -> bool:
    all_valid = True
    for path in sorted(files):
        doc = etree.parse(path)
        if schema.validate(doc):
            print(f"  VALID    {path.name}")
        else:
            all_valid = False
            print(f"  INVALID  {path.name}")
            for err in schema.error_log:
                msg = re.sub(r"\{https?://[^}]+\}", "", err.message)
                print(f"           Line {err.line}: {msg}")
    return all_valid


def main():
    files = list(XML_DIR.glob("crossref-*.xml")) if len(sys.argv) == 1 else [Path(p) for p in sys.argv[1:]]
    if not files:
        print("No XML files found.")
        sys.exit(1)

    schema = load_schema()
    ok = validate(files, schema)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
