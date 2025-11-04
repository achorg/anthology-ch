# Anthology of Computers and the Humanities

This repository contains the source code and build system for the [Anthology of Computers and the Humanities](https://anthology.ach.org/) website.

The Anthology is a low-cost, open-access, and easy-to-maintain digital archive that hosts peer-reviewed conference papers from digital humanities conferences and workshops. The archive is indexed across popular scholarly indices and includes support for persistent identifiers including DOIs (Digital Object Identifiers) and ORCID iDs.

## Setup

This project uses [uv](https://docs.astral.sh/uv/) for Python package and environment management.

### Prerequisites

- Python 3.13 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- XeLaTeX (for PDF compilation)
- Pandoc (for HTML generation)

### Installation

1. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Clone this repository:
   ```bash
   git clone https://github.com/dh-tech/anthology-ch.git
   cd anthology-ch
   ```

3. Install the project and its dependencies:
   ```bash
   uv sync
   ```

4. The build tool will be available as the `anthology` command:
   ```bash
   uv run anthology --help
   ```

## Build Process

The build system operates in two distinct phases: **prepare** and **build**.

### Phase 1: Prepare

The `prepare` command copies input files from the `input/` directory to the `docs/volumes/` output directory and prepares them for building.

```bash
uv run anthology prepare [OPTIONS]
```

**Options:**
- `-v, --verbose` - Show detailed output
- `--volume <name>` - Prepare only a specific volume (e.g., 'vol0001' or '1')

**What it does:**
1. Adds DOIs to papers with placeholder values
2. Copies LaTeX files, bibliographies, and figures to the output directory
3. Sets paper order numbers within each volume
4. Saves metadata for input-independent building

**Example:**
```bash
# Prepare all papers
uv run anthology prepare

# Prepare only volume 1 with verbose output
uv run anthology prepare --volume 1 --verbose
```

After this step, papers can be built without access to the input directory.

### Phase 2: Build

The `build` command compiles papers from the output directory and generates all necessary files for the website.

```bash
uv run anthology build [OPTIONS]
```

**Options:**
- `-v, --verbose` - Show detailed output and LaTeX errors
- `--volume <name>` - Build only a specific volume (e.g., 'vol0001' or '1')

**What it does:**
1. Discovers papers in the output directory
2. Compiles papers to PDF using XeLaTeX
3. Adds metadata (page numbers, volume info)
4. Recompiles with final metadata
5. Cleans auxiliary files
6. Renames PDFs to their DOI-based names
7. Generates BibTeX citations
8. Generates HTML versions of papers
9. Generates volume index pages
10. Generates Crossref XML metadata for DOI registration
11. Generates sitemap.xml
12. Generates RSS feed
13. Generates main table of contents

**Example:**
```bash
# Build all papers
uv run anthology build

# Build only volume 2 with verbose output
uv run anthology build --volume 2 --verbose
```

**Important:** Run `anthology prepare` before running `anthology build`.

### Complete Workflow

To build the entire website from scratch:

```bash
# Step 1: Prepare all input files
uv run anthology prepare

# Step 2: Build all outputs
uv run anthology build
```

The generated website will be available in the `docs/` directory, which can be deployed directly to GitHub Pages or any other static hosting service.

## Additional Commands

### Compile Only

Compile papers to PDF without generating other outputs:

```bash
uv run anthology compile [--paper <path>] [--verbose]
```

### Generate Outputs

Generate specific outputs without recompiling:

```bash
# Generate HTML versions
uv run anthology generate html

# Generate BibTeX citations
uv run anthology generate bibtex

# Generate volume pages
uv run anthology generate volumes

# Generate table of contents
uv run anthology generate toc

# Generate Crossref XML
uv run anthology generate xml

# Generate sitemap
uv run anthology generate sitemap

# Generate RSS feed
uv run anthology generate rss

# Generate all outputs
uv run anthology generate all
```

### Clean

Remove LaTeX auxiliary files:

```bash
uv run anthology clean [--verbose]
```

### Validate

Check that all required input files exist:

```bash
uv run anthology validate [--verbose]
```

## Project Structure

```
anthology-ch/
├── anthology/          # Python package source code
│   └── anthology/      # Main package
│       ├── cli.py      # Command-line interface
│       ├── paper.py    # Paper processing logic
│       ├── metadata.py # Metadata handling
│       ├── html_generator.py  # HTML generation
│       ├── xml_generator.py   # Crossref XML generation
│       ├── bibtex.py   # BibTeX generation
│       └── ...
├── data/
│   ├── templates/      # Jinja2 HTML templates
│   └── xml/           # Generated Crossref XML files
├── docs/              # Generated website (output)
│   ├── volumes/       # Volume and paper pages
│   ├── about/         # About page
│   ├── css/          # Stylesheets
│   └── ...
├── input/            # Source LaTeX papers (input)
│   └── vol*/         # Papers organized by volume
├── pyproject.toml    # Project configuration
└── README.md         # This file
```

## License

Papers © 2025 their authors. All other content © 2025 ACH.
