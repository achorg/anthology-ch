#!/bin/zsh 

rm ach-latex-en.zip
rm ach-latex-fr.zip
rm ach-md-en.zip
rm ach-md-fr.zip
rm ach-docx-en.zip
rm ach-docx-fr.zip

mkdir ach-latex-en
cp template-latex/640x480.png ach-latex-en
cp template-latex/anthology-ch.cls ach-latex-en
cp template-latex/bibliography.bib ach-latex-en
cp template-latex/Makefile ach-latex-en
cp template-latex/paper.tex ach-latex-en
cp -R template-latex/fonts ach-latex-en
zip -r ach-latex-en.zip ach-latex-en
rm -rf ach-latex-en

mkdir ach-latex-fr
cp template-latex/640x480.png ach-latex-fr
cp template-latex/anthology-ch.cls ach-latex-fr
cp template-latex/bibliography.bib ach-latex-fr
cp template-latex/Makefile ach-latex-fr
cp template-latex/paper-fr.tex ach-latex-fr/paper.tex
cp -R template-latex/fonts ach-latex-fr
zip -r ach-latex-fr.zip ach-latex-fr
rm -rf ach-latex-fr

mkdir ach-md-en
cp template-md/640x480.png ach-md-en
cp template-md/bibliography.bib ach-md-en
cp template-md/paper.md ach-md-en
zip -r ach-md-en.zip ach-md-en
rm -rf ach-md-en

mkdir ach-md-fr
cp template-md/640x480.png ach-md-fr
cp template-md/bibliography.bib ach-md-fr
cp template-md/paper-fr.md ach-md-fr/paper.md
zip -r ach-md-fr.zip ach-md-fr
rm -rf ach-md-fr

mkdir ach-docx-en
cp template-docx/paper.docx ach-docx-en
zip -r ach-docx-en.zip ach-docx-en
rm -rf ach-docx-en

mkdir ach-docx-fr
cp template-docx/paper-fr.docx ach-docx-fr/paper.docx
zip -r ach-docx-fr.zip ach-docx-fr
rm -rf ach-docx-fr

