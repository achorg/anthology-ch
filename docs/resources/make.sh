#!/bin/zsh

rm -f ach-latex-template.zip

mkdir ach-latex-template
cp template-latex/orcid.png ach-latex-template
cp template-latex/640x480.png ach-latex-template
cp template-latex/anthology-ch.cls ach-latex-template
cp template-latex/bibliography.bib ach-latex-template
cp template-latex/Makefile ach-latex-template
cp template-latex/paper.tex ach-latex-template
cp template-latex/paper-fr.tex ach-latex-template
cp -R template-latex/fonts ach-latex-template
zip -r ach-latex-template.zip ach-latex-template
rm -rf ach-latex-template
