import json
import os
from datetime import date
from pathlib import Path
import subprocess

import polars as pl
from polars import col as c
from TexSoup import TexSoup
from TexSoup.data import BracketGroup, BraceGroup
from jinja2 import Environment, FileSystemLoader


RERUN_XELATEX = False

TEMPLATE_ENV = Environment(loader=FileSystemLoader("templates"))
TEMPLATE_ENV.globals["year"] = date.today().year


def latex_to_html(latex_str, scalar=True):
    if scalar and "\\" not in latex_str:
        return latex_str

    result = subprocess.run(
        ["pandoc", "-f", "latex", "-t", "html"],
        input=latex_str,
        capture_output=True,
        text=True,
    )
    html = result.stdout.strip()

    if scalar and html.startswith("<p>") and html.endswith("</p>"):
        html = html[3:-4]

    return html


def parse_author(node):
    author = {
        "name": None,
        "affiliations": None,
        "orcid": None,
        "email": None,
        "corresponding": None,
    }

    for arg in node.args:
        value = str(arg)[1:-1]

        if isinstance(arg, BraceGroup):
            author["name"] = latex_to_html(value)
        elif isinstance(arg, BracketGroup):
            pairs = dict(
                part.split("=", 1)
                for part in value.split(",")
                if "=" in part
            )
            plain = [
                part.strip()
                for part in value.split(",")
                if "=" not in part and part.strip()
            ]

            if plain:
                author["affiliations"] = plain
            if "orcid" in pairs:
                author["orcid"] = pairs["orcid"].strip()
            if "email" in pairs:
                author["email"] = pairs["email"].strip()
            if "corresponding" in pairs:
                author["corresponding"] = pairs["corresponding"].strip()

    return pl.DataFrame(author)


def parse_affiliation(node):
    args = list(node.args)
    return pl.DataFrame({
        "affiliation_id": str(args[0])[1:-1],
        "affiliation_name": latex_to_html(str(args[1])[1:-1]),
    })


def create_metadata_table():

    df_paper = []
    df_author = []
    df_aff = []

    papers = sorted(list(Path("docs/volumes/").glob("vol*/*/paper.tex")))

    for paper in papers:
        #try:
            sp = TexSoup(paper.read_text(), tolerance=1)

            df_paper.append(pl.DataFrame({
                "title": latex_to_html(" ".join(sp.find("title").text)),
                "pubyear": " ".join(sp.find("pubyear").text),
                "pubvolume": " ".join(sp.find("pubvolume").text),
                "pagestart": " ".join(sp.find("pagestart").text),
                "pageend": " ".join(sp.find("pageend").text),
                "paperorder": " ".join(sp.find("paperorder").text),
                "conferencename": " ".join(sp.find("conferencename").text),
                "conferenceeditors": " ".join(sp.find("conferenceeditors").text),
                "doi": " ".join(sp.find("doi").text),
                "abstract": latex_to_html(
                    " ".join(sp.find("abstract").text),
                    scalar=False
                ),
                "keywords": latex_to_html(" ".join(sp.find("keywords").text) if sp.find("keywords") else ""),
                "directory": str(paper.parent),
                "slug": paper.parent.name,
                "vol_slug": paper.parent.parent.name
            }))

            slug = paper.parent.name
            df_author += [parse_author(x).with_columns(pl.lit(slug).alias("slug")) for x in sp.find_all("author")]
            df_aff += [parse_affiliation(x).with_columns(pl.lit(slug).alias("slug")) for x in sp.find_all("affiliation")]

        #except:
        #    print(f"Problem with {str(paper)}")


    auth_schem = {
        "name": pl.String, "affiliations": pl.String, "orcid": pl.String, "slug": pl.String
    }

    df_paper = pl.concat(df_paper).sort(c.vol_slug, c.paperorder)
    df_author = pl.concat([d.cast(auth_schem) for d in df_author])
    df_aff = pl.concat(df_aff)

    vol_meta = json.loads(Path("static/metadata.json").read_text())
    df_volume = pl.DataFrame([{"vol_slug": k, **v} for k, v in vol_meta.items()])

    df_paper.write_parquet("db/paper.parquet")
    df_author.write_parquet("db/author.parquet")
    df_aff.write_parquet("db/affiliation.parquet")
    df_volume.write_parquet("db/volume.parquet")


def create_paper_pages():

    df_paper = pl.read_parquet("db/paper.parquet")
    df_author = pl.read_parquet("db/author.parquet")
    df_aff = pl.read_parquet("db/affiliation.parquet")
    df_volume = pl.read_parquet("db/volume.parquet")

    paper_template = TEMPLATE_ENV.get_template("article.html")

    for paper in df_paper.iter_rows(named=True):
        vol = df_volume.filter(c.vol_slug == paper["vol_slug"]).row(0, named=True)
        doi_file = paper["doi"].replace("/", "@")
        base_url = f"https://anthology.ach.org/volumes/{paper['vol_slug']}/{paper['slug']}/"

        paper_authors = (
            df_author.filter(c.slug == paper["slug"])
            .group_by(["name", "orcid"], maintain_order=True)
            .agg(c.affiliations.alias("affiliation_numbers"))
        ).to_dicts()

        paper_affs = [
            {"number": int(r["affiliation_id"]), "text": r["affiliation_name"]}
            for r in df_aff.filter(c.slug == paper["slug"]).iter_rows(named=True)
            if r["affiliation_id"].isdigit()
        ]

        cite_authors = [
            {"last": a["name"].rsplit(" ", 1)[-1], "first": a["name"].rsplit(" ", 1)[0]}
            for a in paper_authors
        ]
        cite_editors = [
            {"last": e.rsplit(" ", 1)[-1], "first": e.rsplit(" ", 1)[0]}
            for e in paper["conferenceeditors"].split(", ")
        ]

        output = paper_template.render(
            cite_paper_title=paper["title"],
            cite_paper_url=base_url,
            cite_date=paper["pubyear"],
            cite_volume=paper["pubvolume"],
            cit_first_page=paper["pagestart"],
            cite_last_page=paper["pageend"],
            cite_doi=paper["doi"],
            cite_authors=cite_authors,
            cite_editors=cite_editors,
            cite_abstract=paper["abstract"],
            cite_language="en",
            cite_keywords=[k.strip() for k in paper["keywords"].split(",")],
            cite_html_url=base_url,
            cite_pdf_url=base_url + doi_file + ".pdf",
            volume=paper["pubvolume"],
            title=paper["title"],
            authors=paper_authors,
            affiliations=paper_affs,
            pdf_path=doi_file + ".pdf",
            bib_path=doi_file + ".bib",
            doi=paper["doi"],
            date=vol["pubdate"],
            kwords=paper["keywords"],
            content=f'<div class="abs"><span>Abstract</span><p>{paper["abstract"]}</p></div>',
        )
        (Path(paper["directory"]) / "index.html").write_text(output)


def create_volume_pages():

    df_paper = pl.read_parquet("db/paper.parquet")
    df_author = pl.read_parquet("db/author.parquet")
    df_volume = pl.read_parquet("db/volume.parquet")

    volume_template = TEMPLATE_ENV.get_template("volume.html")

    for vol in df_volume.iter_rows(named=True):
        vol_papers = df_paper.filter(c.vol_slug == vol["vol_slug"])

        papers = []
        for paper in vol_papers.iter_rows(named=True):
            authors = df_author.filter(c.slug == paper["slug"])["name"].unique(maintain_order=True).to_list()
            papers.append({
                "url": f"{paper['slug']}/",
                "title": paper["title"],
                "authors": authors,
                "pagestart": paper["pagestart"],
                "pageend": paper["pageend"],
            })

        html = volume_template.render(
            title=f"Volume {vol['pubvolume']} · Anthology of Computers and the Humanities",
            pubvolume=vol["pubvolume"],
            date=vol["date"],
            description=vol["description"],
            conferencename=vol["conferencename"],
            conferenceeditors=vol["conferenceeditors"],
            papers=papers,
        )
        (Path("docs/volumes") / vol["vol_slug"] / "index.html").write_text(html)



def create_front_pages():

    df_paper = pl.read_parquet("db/paper.parquet")
    df_volume = pl.read_parquet("db/volume.parquet")

    paper_counts = df_paper.group_by("vol_slug").agg(c.slug.count().alias("num_papers"))
    df_volume = df_volume.join(paper_counts, on="vol_slug", how="left")

    volumes = [
        {**row, "url": f"{row['vol_slug']}/"}
        for row in df_volume.iter_rows(named=True)
    ]

    Path("docs/index.html").write_text(TEMPLATE_ENV.get_template("main.html").render(volumes=volumes))
    Path("docs/volumes/index.html").write_text(TEMPLATE_ENV.get_template("toc.html").render(volumes=volumes))


def create_bibtex():

    df_paper = pl.read_parquet("db/paper.parquet")
    df_author = pl.read_parquet("db/author.parquet")
    df_volume = pl.read_parquet("db/volume.parquet")

    for paper in df_paper.iter_rows(named=True):
        vol = df_volume.filter(c.vol_slug == paper["vol_slug"]).row(0, named=True)
        doi_file = paper["doi"].replace("/", "@")
        authors = df_author.filter(c.slug == paper["slug"])["name"].unique(maintain_order=True).to_list()

        bib = f"""@article{{{doi_file},
  title = {{{paper["title"]}}},
  author = {{{" and ".join(authors)}}},
  year = {{{paper["pubyear"]}}},
  journal = {{Anthology of Computers and the Humanities}},
  volume = {{{paper["pubvolume"]}}},
  pages = {{{paper["pagestart"]}--{paper["pageend"]}}},
  editor = {{{vol["conferenceeditors"]}}},
  doi = {{{paper["doi"]}}}
}}"""

        (Path(paper["directory"]) / f"{doi_file}.bib").write_text(bib)


def create_pdf():

    df_paper = pl.read_parquet("db/paper.parquet")

    project_root = Path(__file__).resolve().parent
    tex_env = os.environ.copy()
    tex_env["TEXINPUTS"] = f"{project_root / 'static'}//:{project_root / 'fonts'}//:"

    for paper in df_paper.iter_rows(named=True):
        paper_dir = Path(paper["directory"])
        doi_file = paper["doi"].replace("/", "@")

        if not RERUN_XELATEX and (paper_dir / f"{doi_file}.pdf").exists():
            continue

        for cmd in [
            ["xelatex", "-interaction=nonstopmode", "paper.tex"],
            ["biber", "paper"],
            ["xelatex", "-interaction=nonstopmode", "paper.tex"],
            ["xelatex", "-interaction=nonstopmode", "paper.tex"],
        ]:
            result = subprocess.run(cmd, env=tex_env, cwd=paper_dir,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if result.returncode != 0:
                print(f"Problem with {paper['slug']} at {cmd[0]}")
                break
        else:
            (paper_dir / "paper.pdf").rename(paper_dir / f"{doi_file}.pdf")


def create_xml_records():

    df_paper = pl.read_parquet("db/paper.parquet")
    df_author = pl.read_parquet("db/author.parquet")
    df_volume = pl.read_parquet("db/volume.parquet")

    BASE = "https://anthology.ach.org"

    # --- sitemap.xml ---
    static_urls = [
        (f"{BASE}/", "monthly", "1.0", None),
        (f"{BASE}/volumes/", "monthly", "0.9", None),
        (f"{BASE}/about/", "yearly", "0.7", None),
    ]

    url_tags = "\n".join(
        f"  <url>\n    <loc>{loc}</loc>\n    <changefreq>{freq}</changefreq>\n    <priority>{pri}</priority>"
        + (f"\n    <lastmod>{mod}</lastmod>" if mod else "")
        + "\n  </url>"
        for loc, freq, pri, mod in static_urls
    )

    for vol in df_volume.iter_rows(named=True):
        url_tags += (
            f"\n  <url>\n    <loc>{BASE}/volumes/{vol['vol_slug']}/</loc>\n"
            f"    <changefreq>yearly</changefreq>\n    <priority>0.8</priority>\n"
            f"    <lastmod>{vol['pubdate']}</lastmod>\n  </url>"
        )

    for paper in df_paper.iter_rows(named=True):
        vol = df_volume.filter(c.vol_slug == paper["vol_slug"]).row(0, named=True)
        url_tags += (
            f"\n  <url>\n    <loc>{BASE}/volumes/{paper['vol_slug']}/{paper['slug']}/</loc>\n"
            f"    <changefreq>yearly</changefreq>\n    <priority>0.6</priority>\n"
            f"    <lastmod>{vol['pubdate']}</lastmod>\n  </url>"
        )

    Path("docs/sitemap.xml").write_text(
        f'<?xml version="1.0" ?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{url_tags}\n</urlset>\n'
    )

    # --- rss.xml ---
    from email.utils import formatdate
    build_date = formatdate(usegmt=True)

    items = ""
    for paper in df_paper.iter_rows(named=True):
        authors = df_author.filter(c.slug == paper["slug"])["name"].unique(maintain_order=True).to_list()
        url = f"{BASE}/volumes/{paper['vol_slug']}/{paper['slug']}/"
        creator_tags = "".join(f"\n      <dc:creator>{a}</dc:creator>" for a in authors)
        items += (
            f"\n    <item>"
            f"\n      <title>{paper['title']}</title>"
            f"\n      <link>{url}</link>"
            f"\n      <guid>{url}</guid>"
            f"{creator_tags}"
            f"\n      <dc:identifier>https://doi.org/{paper['doi']}</dc:identifier>"
            f"\n    </item>"
        )

    Path("docs/rss.xml").write_text(
        f'<?xml version="1.0" ?>\n'
        f'<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">\n'
        f'  <channel>\n'
        f'    <title>Anthology of Computers and the Humanities</title>\n'
        f'    <link>{BASE}</link>\n'
        f'    <description>Anthology of Computers and the Humanities (ACH) is an open-access journal publishing technical papers, software documentation, and research in digital humanities.</description>\n'
        f'    <language>en</language>\n'
        f'    <lastBuildDate>{build_date}</lastBuildDate>\n'
        f'    <atom:link href="{BASE}/rss.xml" rel="self" type="application/rss+xml"/>'
        f'{items}\n'
        f'  </channel>\n'
        f'</rss>\n'
    )


def create_crossref_xml():

    import uuid
    from datetime import datetime

    df_paper = pl.read_parquet("db/paper.parquet")
    df_author = pl.read_parquet("db/author.parquet")
    df_volume = pl.read_parquet("db/volume.parquet")

    BASE = "https://anthology.ach.org"
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d%H%M%S") + str(now.microsecond // 1000).zfill(3)

    for vol in df_volume.iter_rows(named=True):
        dt = datetime.strptime(vol["pubdate"], "%d %B %Y")
        month, day, year = dt.strftime("%m"), dt.strftime("%d"), dt.strftime("%Y")

        articles = ""
        for paper in df_paper.filter(c.vol_slug == vol["vol_slug"]).iter_rows(named=True):
            paper_authors = (
                df_author.filter(c.slug == paper["slug"])
                .group_by(["name", "orcid"], maintain_order=True)
                .agg(c.affiliations)
            ).to_dicts()

            contributors = ""
            for i, a in enumerate(paper_authors):
                seq = "first" if i == 0 else "additional"
                given = a["name"].rsplit(" ", 1)[0]
                surname = a["name"].rsplit(" ", 1)[-1]
                orcid_tag = f"\n            <ORCID>https://orcid.org/{a['orcid']}</ORCID>" if a["orcid"] else ""
                contributors += (
                    f'\n          <person_name sequence="{seq}" contributor_role="author">'
                    f"\n            <given_name>{given}</given_name>"
                    f"\n            <surname>{surname}</surname>"
                    f"{orcid_tag}"
                    f"\n          </person_name>"
                )

            url = f"{BASE}/volumes/{paper['vol_slug']}/{paper['slug']}/"
            articles += f"""
      <journal_article publication_type="full_text">
        <titles>
          <title>{paper["title"]}</title>
        </titles>
        <contributors>{contributors}
        </contributors>
        <publication_date media_type="print">
          <month>{month}</month>
          <day>{day}</day>
          <year>{year}</year>
        </publication_date>
        <pages>
          <first_page>{paper["pagestart"]}</first_page>
          <last_page>{paper["pageend"]}</last_page>
        </pages>
        <doi_data>
          <doi>{paper["doi"]}</doi>
          <resource>{url}</resource>
        </doi_data>
      </journal_article>"""

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<doi_batch xmlns="http://www.crossref.org/schema/4.4.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:jats="http://www.ncbi.nlm.nih.gov/JATS1" version="4.4.2" xsi:schemaLocation="http://www.crossref.org/schema/4.4.2 http://www.crossref.org/schema/deposit/crossref4.4.2.xsd">
  <head>
    <doi_batch_id>{uuid.uuid4().hex[:23]}</doi_batch_id>
    <timestamp>{timestamp}</timestamp>
    <depositor>
      <depositor_name>taylor@dvlab.org:4chu</depositor_name>
      <email_address>tarnold2@richmond.edu</email_address>
    </depositor>
    <registrant>WEB-FORM</registrant>
  </head>
  <body>
    <journal>
      <journal_metadata>
        <full_title>Anthology of Computers and the Humanities</full_title>
        <abbrev_title>Anth. Comp. Hum.</abbrev_title>
        <doi_data>
          <doi>10.63744/GJCCSMz4QBbD</doi>
          <resource>{BASE}/</resource>
        </doi_data>
      </journal_metadata>
      <journal_issue>
        <publication_date media_type="print">
          <month>{month}</month>
          <day>{day}</day>
          <year>{year}</year>
        </publication_date>
        <journal_volume>
          <volume>{vol["pubvolume"]}</volume>
        </journal_volume>
      </journal_issue>{articles}
    </journal>
  </body>
</doi_batch>
"""
        Path(f"xml/crossref-{vol['vol_slug']}.xml").write_text(xml)


def main():
    create_metadata_table()

    #create_pdf()
    create_bibtex()
    create_xml_records()

    create_paper_pages()
    create_volume_pages()
    create_front_pages()

if __name__ == "__main__":
    main()
