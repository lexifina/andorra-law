# The laws of Andorra, as enacted, as a git repository

The laws of the Principality of Andorra as a git repository: the Constitution of 1993 and {{LAWS}} laws (lleis) of the Consell General, from {{FIRST_PUBLISHED}} to {{LAST_PUBLISHED}}, each as the Butlletí Oficial del Principat d'Andorra (BOPA) published it. There is one file per article, disposition or annex ({{UNITS}} files), plus each law's preamble and signatures, with one paragraph per line, so `git blame` and `git diff` work line by line. The text is in Catalan, the official language.

**What this repository is: each law as enacted, not a consolidated history.** The BOPA publishes each law once, as passed. It publishes no consolidated texts with dated past versions; when Andorra consolidates a law, it does so by passing a new law ("Llei N/AAAA ... del text consolidat de ..."), which is here as a law in its own right. So each law is one commit holding its text as enacted, dated by the day it entered into force. **Amendments are not applied**: when a later law changes an article, the earlier law's file here still shows the text as first enacted. The changes later laws state ("Es modifica l'article 5 de la Llei 3/2010...") are listed, law by law, in [`data/amendments.csv`](data/amendments.csv) ({{AMENDMENT_ROWS}} rows). There is no line-by-line history of any law's text before or after its enactment.

The record holds {{COMMITS_MAIN}} commits on `main` ({{LAW_COMMITS}} laws, in force from {{FIRST}} to {{LAST}}, and one documentation commit) and {{FUTURE}} laws on the branch `future`, which enter into force after {{TODAY}}.

## A lawyer's questions as git commands

| Question | Command |
| --- | --- |
| What does article 4 of the copyright law of 1999 say, as enacted? | `python tools/in_force_on.py {{TODAY}} {{COPYRIGHT_DIR}} article-004` |
| The whole of a law, in order | `python tools/in_force_on.py {{TODAY}} lleis/2022-041` |
| Was a law in force on a date? | `python tools/in_force_on.py 2022-12-15 lleis/2022-041` |
| Which later laws say they change Llei 15/2021? | `grep ',lleis/2021-015,' data/amendments.csv` |
| What a law says about its own entry into force | `git log -1 --format=%B -- lleis/2022-041` |
| Which laws were in force by a date | `git log --format='%(trailers:key=In-force,valueonly,separator=) %s' main` |
| Laws not yet in force | `git log main..future --format=%s` |
| The list of laws, with their dates | [`laws.csv`](laws.csv) |
| Every citation of an article number | `git grep -E "[Aa]rticles? 25([^0-9]|$)" -- lleis/2022-041` |

Each law has its own folder: `constitucio/` for the Constitution, `lleis/2022-041/` for Llei 41/2022 (year, then the number), and, for the laws before numbering began (about 2000), `lleis/<publication date>-<BOPA document id>/`. In it: `preamble.md` (the title, the enacting words, the statement of reasons and any table of contents), one file per article (`article-001.md`, `article-004-bis.md`, `article-unic.md`), one per disposition (`disposicio-final-primera.md`, `disposicio-derogatoria.md`), one per annex, and `signatures.md` (the place and date, the signatures and the co-princes' promulgation). `index.txt` lists the files in the law's order. Each file starts with any Títol, Capítol or Secció heading above it (`## Capítol segon. ...`), then its own heading (`# Article 4. ...`), then its paragraphs, one per line. Tables are one row per line, cells separated by ` | `.

## The dates, and which one we use

Every law commit is dated by the day the law entered into force, at noon Andorra time (Central European Time, with summer time as in the EU), and the date is in its `In-force:` trailer. The trailer `In-force-basis:` says where the date comes from:

- {{BASIS_OWN}} laws say when they enter into force (`entra en vigor l'endemà de ser publicada`, `al cap de vint dies`, `l'1 de gener del 2023`). The date is counted from the BOPA publication date, which is in the `Published:` trailer. The commit message quotes the sentence.
- {{BASIS_DEFAULT}} laws say nothing about it. They are dated by the general rule of the Codi de l'Administració of 29 March 1989, article 9 ("Llevat que es disposi altrament per llei dels Coprínceps o del Consell General, les normes jurídiques entraran en vigor als quinze dies de llur publicació íntegra"): fifteen days after publication.
- {{BASIS_PUBLICATION}} laws published before that Code are dated by their publication date.

Where a law names a day before its own publication date (a budget law published after 1 January, for example), the commit carries the day it names. A provision that enters into force on a different day from the rest of its law is not separated out; it carries its law's date.

`tools/in_force_on.py` answers for any date: before a law's in-force date it says the law was not yet in force; after it, it prints the text as enacted and warns that later amendments are not applied.

## What "author" means

Each law commit is authored by the law itself: `Llei 41/2022 <llei-2022-41@bopa-ad.invalid>`, or for the Constitution `Constitució del Principat d'Andorra <constitucio-1993@bopa-ad.invalid>`. The addresses cannot exist. The committer is Lexifina. There are no amendment commits: an amending law is a commit of its own text, in its own folder, and is not credited with any line of the law it amends.

## What it does not show

- Any law's text as amended. Changes stated by later laws are rows in [`data/amendments.csv`](data/amendments.csv), extracted automatically from sentences such as "Es modifica l'article 25 del Codi de procediment civil" and "Queda derogada la Llei ...": the amended law as the amending law names it (and its folder here, when it is cited by number), the provision, the kind of change (modification, insertion, repeal, renumbering), the amending law and its in-force date, the file the sentence is in, and the sentence. The extraction is not complete and not checked by hand.
- Corrections of errata ({{CORRECTIONS}} documents). They are listed in [`data/corrections.csv`](data/corrections.csv) and not applied.
- Other legislation (decrees, regulations, the Government's acts), and the laws of the parishes (comuns).
- The links the BOPA website adds to old laws ("Text refós", "Descarrega el document"); they are not part of the law.
- Pictures and the gazette's page layout.

Documents that could not be read or placed are listed in [`data/unreadable.csv`](data/unreadable.csv) ({{UNREADABLE}} rows).

This is a research aid, not an official publication. For anything that matters, read the BOPA. This repository is not made, sponsored or endorsed by the Servei del Butlletí Oficial del Principat d'Andorra.

## How it is checked

`tools/build/` holds the build as it was run. [`data/source-sha256.tsv`](data/source-sha256.tsv) has the sha256 of every BOPA document the build read, and each commit names its document (`Source:`, `Source-sha256:`). The build is deterministic: from the same documents it gives the same commit hashes. See [`REPRODUCE.md`](REPRODUCE.md). Before publishing, the build was checked for these things:
- the letters and digits of every law's files, in order, equal those of the BOPA document it came from (with the site's added links taken out), checked by a separate script that does not use the build's parser;
- `tools/in_force_on.py` gives the right answer for sample articles at several dates;
- every commit's trailers parse; there are no merges, no dates that go backwards and no dates after the build date on `main`; no message has a carriage return;
- two builds from the same documents give the same HEAD.

## How it is built

`fetch.py` reads the BOPA's own public search (the requests its website makes) for every document under the themes "Lleis" and "Constitució", year by year, and downloads each document's HTML from the BOPA document store. Long documents are listed in the search as chunks (`1_<id>.html`, `2_<id>.html`); the whole document is `<id>.html` in the same folder, and that is what is read. `parse.py` turns the HTML into paragraphs (old documents are printed lines, joined back into paragraphs) and splits them at the law's own article headings; `inforce.py` reads the entry-into-force provision; `build.py` writes one commit per law with `git fast-import`. No AI model takes part in building or checking it.

## Licence

Source: Butlletí Oficial del Principat d'Andorra, https://www.bopa.ad. Official texts are not protected by copyright in Andorra (Llei sobre drets d'autor i drets veïns, del 10 de juny de 1999, article 4(2): "Cap text oficial de naturalesa legislativa, administrativa o judicial, com tampoc cap traducció oficial seva, queden protegits per aquesta Llei."). The BOPA's legal notice allows copying, distribution, adaptation, extraction, reordering and combination, in any format, on these conditions, quoted as published:

> - Es prohibeix desnaturalitzar el sentit de la informació.
> - Es prohibeix indicar, insinuar o suggerir que Servei del Butlletí Oficial del Principat d'Andorra participa, patrocina o dóna suport a aquesta utilització.
> - Les metadades sobre la data d'actualització i les condicions d'utilització de la informació, si s'inclouen en la informació, s'han de conservar sense alterar-les, i no es poden suprimir.
> - Es prohibeix la utilització de dominis, logotips i elements gràfics que pertanyin al Servei del Butlletí Oficial del Principat d'Andorra, i la seva forma de presentació.

The wording of the laws was not changed. Lexifina's own contributions (the tools, the arrangement and the commit messages) are CC0. See [`LICENSE`](LICENSE) and [`SOURCES.md`](SOURCES.md).
