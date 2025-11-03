---
title: "Here is a Sample Paper Title"
authors:
  - name: Author One
    affiliation: 
      - "Some Department, Some University, Some City, Some Country"
      - "Another Department, Another University, Another City, Another Country"
    orcid: 0000-0000-0000-0000
    email: author@university.com
  - name: Author Two
    affiliation: "Some Department, Some University, Some City, Some Country"
    orcid: 0000-0000-0000-0001
  - name: Author Three
    affiliation: "Another Department, Another University, Another City, Another Country"
    orcid: ""
keywords: [computers, humanities proceedings]
abstract: |
  This Markdown template helps you typeset and format a paper for the ACH Anthology. The abstract of the paper here should be a one-paragraph summary of the outline and main contributions of the paper. Remember to change the keywords in the fields above and to fill in all of the relevant information for each author.
bibliography: bibliography.bib
---

# Introduction

Here is an example of the first section of the paper. All standard markdown
formatting commands work as expected, such as *italic*, **bold**, and `code`.

You may modify this markdown file by renaming, deleting, or adding sections of
your own and substituting our instructional text with the text of your paper. Add
references to `bibliography.bib` as BibTeX entries. These can then be cited
by using the format at the end of this sentence, namely the use of square
brackets with an at sign followed by the resource key name
[@tettoni2024discoverability]. You can also cite multiple papers together using
the format at the end of this sentence [@barré2024latent; @levenson2024textual; @bambaci2024steps].

## Details {#sec:intro_details}

You may also include subsections if they help organize your text, but they are not required. Use as many sections and subsections with whatever names work for your submission.

# Elements

## Tables

Tables can also be added to the document using the standard Markdown table
format. Each table needs a unique label and caption. Below is an example of
a table labeled as tbl:example along with a brief caption.

| Column Name 1 | Column Name 2 |
|---------------|---------------|
| d1            | d2            |
| d1            | d2            |
| d1            | d2            |

Table: Example table and table caption. {#tbl:example}

The table can be referenced as [Table @tbl:example].

## Figures

Figures can also be added to the document. As with tables, each figure needs
a unique label and caption. The format is shown in the lines below. Figure
files themselves should be included along with the submission. 

![Example figure and figure caption.](640x480.png){#fig:example width=40%}

A figure can be cited as [Figure @fig:example].

## Equations

We can include mathematical notations using LaTeX mathematical formatting,
such as:

$$f(y) = x^2$$ {#eq:squared}

The line number of the equation can be cited as [Equation @eq:squared].

## Other References

Finally, you can also cite other sections or subsections of your paper using
the tags that you have used at the end of each of the section titles: [Section @sec:intro_details].

# References

<!-- Bibliography will be automatically generated here from the bibliography file -->

# First Appendix Section {#sec:first-appendix}

Optional appendix sections can be included after the references section.