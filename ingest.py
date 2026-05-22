import json
import random
import re
import shutil
import string
from pathlib import Path

from TexSoup import TexSoup

VOLUME = 4
INPUT_DIR = Path("injest")

DOI_PREFIX = "10.63744"
DOI_CHARS = string.ascii_letters + string.digits
DOI_SUFFIX_LEN = 12
SLUG_MAX_LEN = 60

REQUIRED_FIELDS = ["title", "pagestart", "pageend", "abstract"]


def existing_dois():
    dois = set()
    for tex_path in Path("docs/volumes").glob("vol*/*/paper.tex"):
        m = re.search(r'\\doi\{([^}]+)\}', tex_path.read_text())
        if m:
            dois.add(m.group(1))
    return dois


def generate_doi(taken):
    while True:
        suffix = "".join(random.choices(DOI_CHARS, k=DOI_SUFFIX_LEN))
        doi = f"{DOI_PREFIX}/{suffix}"
        if doi not in taken:
            return doi


def title_to_slug(title):
    title = re.sub(r'<[^>]+>', '', title)
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    if len(slug) <= SLUG_MAX_LEN:
        return slug
    cut = slug[:SLUG_MAX_LEN]
    boundary = cut.rfind('-')
    return cut[:boundary] if boundary > 0 else cut


def set_tex_field(tex, field, value):
    pattern = rf'\\{re.escape(field)}\{{[^}}]*\}}'
    replacement = f'\\{field}{{{value}}}'
    if re.search(pattern, tex):
        return re.sub(pattern, lambda _: replacement, tex)
    return tex.replace(r'\begin{document}', f'{replacement}\n\\begin{{document}}')


def validate(sp, paper_dir):
    errors = []
    for field in REQUIRED_FIELDS:
        node = sp.find(field)
        if not node:
            errors.append(f"missing \\{field}")
    if not list(sp.find_all("author")):
        errors.append("no \\author found")
    return errors


def main():
    vol_slug = f"vol{VOLUME:04d}"

    meta = json.loads(Path("static/metadata.json").read_text())
    if vol_slug not in meta:
        print(f"WARNING: {vol_slug} not found in static/metadata.json — add it before running build.py")
        vol_meta = None
    else:
        vol_meta = meta[vol_slug]

    input_dirs = sorted(d for d in INPUT_DIR.iterdir() if d.is_dir())
    if not input_dirs:
        print(f"No subdirectories found in {INPUT_DIR}/")
        return

    taken = existing_dois()
    out_vol = Path("docs/volumes") / vol_slug
    out_vol.mkdir(parents=True, exist_ok=True)

    for order, paper_dir in enumerate(input_dirs, start=1):
        tex_path = paper_dir / "paper.tex"
        if not tex_path.exists():
            print(f"SKIP  {paper_dir.name}: no paper.tex")
            continue

        raw_tex = tex_path.read_text()
        sp = TexSoup(raw_tex, tolerance=1)

        errors = validate(sp, paper_dir)
        if errors:
            print(f"SKIP  {paper_dir.name}: {', '.join(errors)}")
            continue

        title = " ".join(sp.find("title").text)
        slug = title_to_slug(title)
        out_dir = out_vol / slug

        if out_dir.exists():
            print(f"SKIP  {paper_dir.name}: {vol_slug}/{slug} already exists")
            continue

        doi = generate_doi(taken)
        taken.add(doi)

        shutil.copytree(paper_dir, out_dir)

        tex = (out_dir / "paper.tex").read_text()
        tex = set_tex_field(tex, "doi", doi)
        tex = set_tex_field(tex, "paperorder", str(order))
        if vol_meta:
            tex = set_tex_field(tex, "pubyear", vol_meta["pubyear"])
            tex = set_tex_field(tex, "pubvolume", vol_meta["pubvolume"])
            tex = set_tex_field(tex, "conferencename", vol_meta["conferencename"])
            tex = set_tex_field(tex, "conferenceeditors", vol_meta["conferenceeditors"])
        (out_dir / "paper.tex").write_text(tex)

        print(f"OK    {paper_dir.name} → {vol_slug}/{slug}  order={order}  doi={doi}")

    if vol_meta is None:
        print(f"\nReminder: add {vol_slug} to static/metadata.json, then run build.py")
    else:
        print("\nDone. Run build.py to compile.")


if __name__ == "__main__":
    main()
