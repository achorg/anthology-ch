# Running the build code

To add a new volume:

1. Place the articles (one article per directory) inside of `injest`.
2. Add the volume metadata to `static/metadata.json`.
3. Run `uv run ingest.py`.
4. Run `uv run build.py`, which will build the first version of the new volume.
5. Change the volume number in `pages.py`.
6. Run `uv run pages.py` to get the correct page numbers for the volume.
6. Add the volume slug to the variable `REBUILD_VOL` in build.py.
7. Run `uv run build.py` to rebuild the PDF files.
8. Remove the `REBUILD_VOL` to avoid rebuilding the PDF files in future runs.

To add the metadata to CrossRef:

1. Sign in the Crossref at https://doi.crossref.org/servlet/useragent
2. Click on Submissions => Upload, select "Metadata" and upload the XML file.
3. You should get an email that it succeeded. 

For other updates:

1. Set `REBUILD_VOL` if you need to recreate all of the PDF files from a volume.
2. Run `uv run build.py` to build the HTML pages.
