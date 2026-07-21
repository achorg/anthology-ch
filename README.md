# Running the build code

To add a new volume:

1. Place the articles (one article per directory) inside of `ingest` (see the format below).
2. Add the volume metadata to `static/metadata.json`.
3. Set `VOLUME` in `ingest.py` to the new volume number.
4. Run `uv run ingest.py`.
5. Run `uv run build.py`, which will build the first version of the new volume.
6. Change the volume number in `pages.py`.
7. Run `uv run pages.py` to get the correct page numbers for the volume.
8. Add the volume slug to the variable `REBUILD_VOL` in build.py.
9. Run `uv run build.py` to rebuild the PDF files.
10. Remove the `REBUILD_VOL` to avoid rebuilding the PDF files in future runs.

## Format of an ingest directory

Each article lives in its own subdirectory of `ingest/`. `ingest.py` copies the
whole directory into `docs/volumes/volXXXX/<slug>/`, so include everything the
paper needs to compile and nothing else.

Required in every directory:

- `paper.tex` — must be named exactly this. `ingest.py` skips a directory that
  has no `paper.tex`, and skips it with a warning unless the file defines
  `\title`, `\pagestart`, `\pageend`, an `abstract` environment, and at least
  one `\author`. The `\doi`, `\paperorder`, `\pubyear`, `\pubvolume`,
  `\conferencename`, and `\conferenceeditors` fields are filled in
  automatically during ingest, so their submission values don't matter.
- `bibliography.bib` — the bibliography pulled in by `\addbibresource`. `biber`
  runs against it during the build.
- Any figures or media referenced by `\includegraphics`, kept at the relative
  paths used in `paper.tex` (e.g. a `media/` or `images/` subdirectory).

Not required — the build supplies these itself:

- `anthology-ch.cls` — the canonical class lives in
  `docs/resources/template-latex/` and is found automatically via `TEXINPUTS`.
- The `fonts/` directory — `build.py` reads fonts from the top-level `fonts/`
  and symlinks them into each paper dir at compile time.
- `orcid.png`, `Makefile`, and other template boilerplate — resolved from the
  shared template or unused by the build.

Shipping these extra files is harmless (they're just copied along) but
unnecessary; a minimal directory is `paper.tex`, `bibliography.bib`, and its
figures.

To add the metadata to CrossRef:

1. Sign in the Crossref at https://doi.crossref.org/servlet/useragent
2. Click on Submissions => Upload, select "Metadata" and upload the XML file.
3. You should get an email that it succeeded. 

For other updates:

1. Set `REBUILD_VOL` if you need to recreate all of the PDF files from a volume.
2. Run `uv run build.py` to build the HTML pages.
