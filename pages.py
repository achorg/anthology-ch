import re
import subprocess
from pathlib import Path

from TexSoup import TexSoup

VOLUME = 4
PAGE_START = 1


def get_page_count(pdf_path):
    result = subprocess.run(["pdfinfo", str(pdf_path)], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    raise RuntimeError(f"Could not read page count from {pdf_path}")


def set_tex_field(tex, field, value):
    pattern = rf'\\{re.escape(field)}\{{[^}}]*\}}'
    replacement = f'\\{field}{{{value}}}'
    if re.search(pattern, tex):
        return re.sub(pattern, lambda _: replacement, tex)
    return tex.replace(r'\begin{document}', f'{replacement}\n\\begin{{document}}')


def main():
    vol_slug = f"vol{VOLUME:04d}"
    vol_dir = Path("docs/volumes") / vol_slug

    papers = []
    for paper_dir in sorted(vol_dir.iterdir()):
        if not paper_dir.is_dir():
            continue
        tex_path = paper_dir / "paper.tex"
        if not tex_path.exists():
            continue

        raw_tex = tex_path.read_text()
        sp = TexSoup(raw_tex, tolerance=1)

        doi_node = sp.find("doi")
        order_node = sp.find("paperorder")
        if not doi_node or not order_node:
            print(f"SKIP  {paper_dir.name}: missing \\doi or \\paperorder")
            continue

        doi = " ".join(doi_node.text)
        order = int(" ".join(order_node.text))
        pdf_path = paper_dir / f"{doi.replace('/', '@')}.pdf"

        if not pdf_path.exists():
            print(f"SKIP  {paper_dir.name}: PDF not found")
            continue

        papers.append({"dir": paper_dir, "tex_path": tex_path,
                       "pdf_path": pdf_path, "order": order})

    papers.sort(key=lambda p: p["order"])

    page = PAGE_START
    for p in papers:
        count = get_page_count(p["pdf_path"])
        pagestart, pageend = page, page + count - 1
        page = pageend + 1

        tex = p["tex_path"].read_text()
        tex = set_tex_field(tex, "pagestart", str(pagestart))
        tex = set_tex_field(tex, "pageend", str(pageend))
        p["tex_path"].write_text(tex)

        print(f"{p['order']:3d}.  {p['dir'].name}  →  pp. {pagestart}–{pageend}")

    print(f"\nTotal: {page - PAGE_START} pages across {len(papers)} papers.")
    print("Run build.py to rebuild the site with updated page numbers.")


if __name__ == "__main__":
    main()
