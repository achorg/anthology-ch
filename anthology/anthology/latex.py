"""LaTeX compilation and manipulation operations for the anthology journal processor."""

import os
import re
import subprocess
from pathlib import Path


def get_texinputs_env() -> dict:
    """
    Get environment variables with TEXINPUTS set to the data directory.

    TEXINPUTS tells LaTeX where to find additional style files and resources.
    This function sets it to the project's data directory with recursive search.

    Returns:
        Dictionary of environment variables with TEXINPUTS configured

    Note:
        The trailing // in TEXINPUTS enables recursive subdirectory search.
        The trailing : appends to default search paths rather than replacing them.
    """
    env = os.environ.copy()
    # Get the absolute path to the data directory from the project root
    project_root = Path(__file__).resolve().parent.parent.parent
    # data_dir = project_root / "docs" / "resources" / "template-latex"
    data_dir = project_root / "data"
    # TEXINPUTS needs a trailing // to search subdirectories
    # Using : separator to append to default search paths
    env["TEXINPUTS"] = f"{data_dir}//:"
    return env


def fill_value(text: str, command: str, new_value: str) -> str:
    """
    Replace the value of a LaTeX command in the text.

    Finds the first occurrence of \\command{value} and replaces
    the value inside the braces.

    Args:
        text: The LaTeX text to search and modify
        command: The LaTeX command name (without backslash)
        new_value: The new value to insert

    Returns:
        The modified text with the command value replaced

    Raises:
        ValueError: If no occurrence of the command is found

    Examples:
        >>> fill_value(r"\\title{Old}", "title", "New")
        '\\\\title{New}'
    """
    pattern = rf"\\{command}\{{([^{{}}]+)\}}"
    match = re.search(pattern, text)
    if not match:
        raise ValueError(f"No occurrence of '\\{command}{{...}}' found in: {text!r}")
    return re.sub(pattern, rf"\\{command}{{{new_value}}}", text, count=1)


def extract_missing_bibliography_entries(latex_output: str) -> list[str]:
    """
    Extract missing bibliography entry citations from LaTeX output.

    Parses LaTeX/biblatex warnings for entries that could not be found
    in the bibliography database.

    Args:
        latex_output: The stdout text from XeLaTeX compilation

    Returns:
        List of missing citation keys

    Example output format from biblatex:
        Package biblatex Warning: The following entry could not be found
        (biblatex)                in the database:
        (biblatex)                casties_2019_17353345
        (biblatex)                Please verify the spelling and rerun
        (biblatex)                LaTeX afterwards.
    """
    missing_entries = []
    lines = latex_output.split("\n")

    for i, line in enumerate(lines):
        # Look for the warning about missing entries
        if "The following entry could not be found" in line:
            # The citation key is typically 2 lines after the warning
            if i + 2 < len(lines):
                # Extract the citation key from the continuation line
                # Format: "(biblatex)                citation_key"
                citation_line = lines[i + 2]
                match = re.search(r"\(biblatex\)\s+(\S+)", citation_line)
                if match:
                    citation_key = match.group(1)
                    if citation_key not in missing_entries:
                        missing_entries.append(citation_key)

    return missing_entries


def run_xelatex(output_dir: Path, verbose: bool = False) -> bool:
    """
    Run the XeLaTeX compilation pipeline on paper.tex.

    The pipeline consists of:
    1. XeLaTeX (first pass)
    2. Biber (bibliography processing)
    3. XeLaTeX (second pass - resolve citations)
    4. XeLaTeX (third pass - resolve cross-references)

    Args:
        output_dir: Directory containing paper.tex and where output will be generated
        verbose: If True, print stdout/stderr from LaTeX commands (default: False)

    Returns:
        True if all compilation steps succeeded, False otherwise

    Note:
        When verbose=False, output is suppressed for cleaner logs.
        When verbose=True, you'll see detailed LaTeX output including errors.
    """
    # Configure output based on verbose flag
    if verbose:
        stdout_dest = None
        stderr_dest = None
    else:
        stdout_dest = subprocess.DEVNULL
        stderr_dest = subprocess.DEVNULL

    # First XeLaTeX pass
    result1 = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "paper.tex"],
        env=get_texinputs_env(),
        cwd=output_dir,
        stdout=stdout_dest,
        stderr=stderr_dest,
        text=True,
    )

    # Biber for bibliography
    result2 = subprocess.run(
        ["biber", "paper"],
        env=get_texinputs_env(),
        cwd=output_dir,
        stdout=stdout_dest,
        stderr=stderr_dest,
        text=True,
    )

    # Second XeLaTeX pass
    result3 = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "paper.tex"],
        env=get_texinputs_env(),
        cwd=output_dir,
        stdout=stdout_dest,
        stderr=stderr_dest,
        text=True,
    )

    # Third XeLaTeX pass - always capture output to check for warnings
    result4 = subprocess.run(
        ["xelatex", "-interaction=nonstopmode", "paper.tex"],
        env=get_texinputs_env(),
        cwd=output_dir,
        stdout=subprocess.PIPE if not verbose else None,
        stderr=subprocess.PIPE if not verbose else None,
        text=True,
    )

    # Check for missing bibliography entries in the final pass
    if result4.stdout:
        missing_entries = extract_missing_bibliography_entries(result4.stdout)
        if missing_entries:
            print(f"⚠️  Missing bibliography entries in {output_dir.name}:")
            for entry in missing_entries:
                print(f"   - {entry}")

    # Return True only if all steps succeeded
    if all(r.returncode == 0 for r in [result1, result2, result3, result4]):
        return True
    else:
        if verbose:
            print(f"\n❌ XeLaTeX compilation failed in {output_dir}")
            for i, result in enumerate([result1, result2, result3, result4], 1):
                if result.returncode != 0:
                    step_names = [
                        "XeLaTeX (pass 1)",
                        "Biber",
                        "XeLaTeX (pass 2)",
                        "XeLaTeX (pass 3)",
                    ]
                    print(
                        f"   Failed at step {i}: {step_names[i - 1]} (exit code {result.returncode})"
                    )
        return False
