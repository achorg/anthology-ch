#!/usr/bin/env python3
"""Verify CrossRef XML deposits against the CrossRef 4.4.2 schema using xmlschema."""

import sys
from pathlib import Path
import xmlschema

SCHEMA_PATH = Path(__file__).parent / "schema" / "crossref4.4.2.xsd"
XML_DIR = Path(__file__).parent / "xml"


def main():
    files = (
        sorted(XML_DIR.glob("crossref-*.xml"))
        if len(sys.argv) == 1
        else [Path(p) for p in sys.argv[1:]]
    )
    if not files:
        print("No XML files found.")
        sys.exit(1)

    schema = xmlschema.XMLSchema(str(SCHEMA_PATH))
    all_valid = True

    for path in files:
        errors = list(schema.iter_errors(str(path)))
        if errors:
            all_valid = False
            print(f"  INVALID  {path.name}")
            for err in errors:
                print(f"           {err}")
        else:
            print(f"  VALID    {path.name}")

    sys.exit(0 if all_valid else 1)


if __name__ == "__main__":
    main()
