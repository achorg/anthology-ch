---
title: "Voici un exemple de titre d'article"
authors:
  - name: Auteur Un
    affiliation: 
      - "Un département, Une université, Une ville, Un pays"
    orcid: 0000-0000-0000-0000
    email: author1@local.fr
  - name: Auteur Deux
    affiliation: "Un département, Une université, Une ville, Un pays"
    orcid: 0000-0000-0000-0001
    email: author2@local.fr
  - name: Author Three
    affiliation: "Un autre département, Une autre université, Une autre ville, Un autre pays"
    orcid: ""
keywords: [computers, humanities proceedings]
abstract: |
  Ce modèle Markdown vous aide à composer et formater un article dans l'Anthologie d'ACH. En pratique, le résumé de l'article doit être un paragraphe rédigé en anglais synthétisant le plan et les principales contributions de l'article. 
bibliography: bibliography.bib
---

# Introduction

Voici un exemple de première section de l'article. Toutes les commandes de
formatage Markdown standard fonctionnent comme prévu, telles que
*italique*, **gras** et `code`


Vous pouvez modifier ce document en renommant, supprimant ou ajoutant vos
propres sections et en remplaçant notre texte explicatif par celui de votre
article. Ajoutez vos références bibliographiques dans `biblography.bib`
au format BibTeX. Vous pouvez les citer comme à la fin de cette phrase
[@tettoni2024discoverability]. Vous pouvez également citer plusieurs
références comme indiqué ici [@barré2024latent; @levenson2024textual; @bambaci2024steps].

## Détails {#sec:intro_details}

Vous pouvez également inclure des sous-sections si elles aident à organiser votre texte, mais ce n'est pas obligatoire. Utilisez autant de sections et sous-sections que nécessaire avec les intitulés qui conviennent à votre soumission!

# Éléments

## Tableaux

Des tableaux peuvent également être ajoutés au document en utilisant le format
de tableau standard. Chaque tableau doit avoir une étiquette unique et
une légende. Vous trouverez ci-dessous (dans le code source) un exemple
de code permettant de créer un tableau, accompagné d'une brève légende.

| Column Name 1 | Column Name 2 |
|---------------|---------------|
| d1            | d2            |
| d1            | d2            |
| d1            | d2            |

Tableau : Exemple de tableau et légende. {#tbl:example}

Nous pouvons citer le [Tableau @tbl:example].

## Figures

Des figures peuvent également être ajoutées au document. Comme pour les
tableaux, chaque figure doit être accompagnée d'une étiquette uniques et
d'une légende. Le format est indiqué dans les lignes ci-dessous
(dans le code source). Les fichiers des figures doivent être joints à la
soumission.

![Exemple de figure et légende.](640x480.png){#fig:example width=40%}

Nous pouvons citer le Figure [Figure @fig:example].

## Equations

Nous pouvons aussi inclure des notations mathématiques, par exemple :

$$f(y) = x^2$$ {#eq:squared}

Le numéro de l'équation peut être cité comme [Équation @eq:squared].

## Other References

Enfin, vous pouvez également citer d'autres sections ou sous-sections de
votre article en utilisant les balises que vous avez utilisées à la fin
de chacun des titres de section : [Section @sec:intro_details].

# Références

<!-- La bibliographie sera automatiquement générée ici à partir du fichier bibliographique. -->

# Première section de l'annexe {#sec:first-appendix}

Des annexes facultatives peuvent être ajoutées après la section des références. 
