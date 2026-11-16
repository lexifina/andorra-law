# Andorran law in 20 charts

[Català](README.md) · **English**

Charts on every country's law, from the whole of global-law: [global-law visualisations/](https://github.com/lexifina/global-law/tree/main/visualisations). These are the charts on Andorra alone.

Twenty charts on Andorran law, drawn only from the data in this repository: the 1993 Constitution and the 1,040 texts of the Consell General that the Butlletí Oficial del Principat d'Andorra (BOPA) has published as laws since 1989, each as enacted (`lleis/`, `constitucio/`, `laws.csv`); the git history, one commit per law dated the day it entered into force; the signatures and preambles of each law; and the 4,048 changes later laws state (`data/amendments.csv`).

Open [`el-dret-andorra-en-20-grafics.html`](el-dret-andorra-en-20-grafics.html) in a browser. The page is one file with all its data inside; it loads only the d3 library and its fonts from the web. The controls at the top right switch the language (Catalan or English) and the theme (light or dark). Each chart names its data path in the repository, its record count and its limits, and has a table of every number under it. Hover over a mark for the exact values.

The charts are descriptive: they show what the record holds, not why.

## The charts

### I. The laws of the Consell General

#### 1. The laws by year

1,026 laws since 1989, by kind and by Síndic General's term; in 2010, 90, of which 73 extraordinary or supplementary credit laws.

![The laws by year](stills/en/01.png)

#### 2. What they are about

The laws by subject and period: budget and credit laws are 51% of those of 2009–2013 and 5% of those of 2019–2023.

![What they are about](stills/en/02.png)

#### 3. The Constitution

The 107 articles of the 1993 Constitution, by title, by how many laws cite them: 142 laws cite it by article number; the most cited is article 10 (16 laws).

![The Constitution](stills/en/03.png)

#### 4. Qualified laws

120 qualified laws by matter and by term: 36 on criminal law, and 7 in 1993, the year of the Constitution.

![Qualified laws](stills/en/04.png)

#### 5. The codes

The editions of each code: three criminal codes (1990, 2005 and 2026), the 2018 Code of Civil Procedure, the longest law, and no civil code.

![The codes](stills/en/05.png)

#### 6. Length

The median new law grows from 1,100 words (1989–1992) to 7,451 (since 2020); the longest laws.

![Length](stills/en/06.png)

### II. How a law is made: sanction, calendar, publication and entry into force

#### 7. The co-princes

The laws each co-prince signed: 28 carry only one co-prince's signature, 16 the French president's alone and 12 the Bishop of Urgell's alone.

![The co-princes](stills/en/07.png)

#### 8. The calendar

The day the Consell General approves its laws: 68% on a Thursday; December has the most laws and August only 2.

![The calendar](stills/en/08.png)

#### 9. From approval to the BOPA

The days until publication in the BOPA, by term: a median of 26; 19 in Roser Suñé Pascuet's.

![From approval to the BOPA](stills/en/09.png)

#### 10. Entry into force

48% of laws enter into force the day after publication and 33% the same day: up to 1999, 79% the same day; since 2010, 70% the next day.

![Entry into force](stills/en/10.png)

#### 11. The anatomy of a law

The provisions of each new law and its statement of reasons: final provisions go from 1.0 to 4.9 on average.

![The anatomy of a law](stills/en/11.png)

#### 12. The words of entry into force

"La present Llei" gives way to "Aquesta Llei" (from 34% of the clauses to 2%), and the present tense "entra" gains on the future "entrarà".

![The words of entry into force](stills/en/12.png)

### III. How the laws change

#### 13. Stated changes

4,048 changes stated by later laws, by year; 36% in laws not titled as amendments.

![Stated changes](stills/en/13.png)

#### 14. The most amended laws

The 15 laws to which the most laws state changes: the 2005 Criminal Code and the 2008 Social Security Act, 29 each.

![The most amended laws](stills/en/14.png)

#### 15. Laws amended later

68% of the new laws of 2011–2019 have received changes stated by a later law; 49% across the record.

![Laws amended later](stills/en/15.png)

#### 16. Consolidated texts

26 consolidated texts since 2020, from the original text to the consolidated one, with the laws stating changes in between; that of the Administration Code, 34 years after the code.

![Consolidated texts](stills/en/16.png)

### IV. Money, taxes and Europe

#### 17. Budgets and credits

Only 6 of the 35 budgets are approved before 1 January; no budget law for 1991, 2010 and 2011; each year's credit laws.

![Budgets and credits](stills/en/17.png)

#### 18. Taxes

Each tax, year by year: corporate tax in 2010, IGI in 2012, personal income tax in 2014; the most amended, the consumption duties (24 laws).

![Taxes](stills/en/18.png)

#### 19. The currency of the laws

Pesetas in 58% of the laws of 1989–2001, euros in 67% since 2003; French francs, in 2 laws.

![The currency of the laws](stills/en/19.png)

#### 20. Europe and international bodies

The European Union, the Monetary Agreement, the Council of Europe, the United Nations, the OECD and the FATF by period: the EU in 31% of the laws of 2019–2023; 76 directives cited by number.

![Europe and international bodies](stills/en/20.png)

## Data

| Dataset | Where in the repository | Records | Coverage |
| --- | --- | ---: | --- |
| Laws and Constitution | `lleis/<year>-<number>/`, `constitucio/`, `laws.csv` | the Constitution and 1,040 texts (1,026 laws and 14 edicts, budget tables and correcting decrees); 30,708 files, 26,437 articles | BOPA, 29 January 1989 to 28 October 2026; each law as enacted |
| History | git log of `main` and `future` (`In-force:`, `In-force-basis:`, `Published:`, `Bulletin:`) | 1,041 law commits | one commit per law, dated the day it enters into force, quoting the law's sentence on its entry into force; 3 laws on `future` |
| Signatures and preambles | `signatures.md`, `preamble.md` | 1,026 laws | the Síndic General, the co-princes, the day and session of approval, the statement of reasons |
| Stated changes | `data/amendments.csv` | 4,048 changes (4,031 with the law identified) | the changes later laws state, extracted automatically |

## Limits

- **Each law as enacted.** The BOPA publishes no consolidated versions and the repository applies no amendments. The charts on changes (13 to 16) count those later laws state in `data/amendments.csv`, an automatic extraction that is neither complete nor checked by hand (before 2004 it finds few).
- **Only the laws of the Consell General.** Government decrees and regulations and the ordinances of the comuns are not included.
- **Categories are read from titles** with the rules in `src/prep.py`: the kind of law, whether it is qualified (when the title says so), the subject, the tax and the code; whatever no rule recognises counts as "other". 14 texts under the BOPA's "Lleis" theme are edicts, budget tables and correcting decrees and do not count as laws.
- **Approval dates** are each law's citation date or, failing that, the Síndic's signature date. Two laws of 1993 are dated a day after the bulletin that publishes them and are left out of chart 9. The preamble and signature of Law 2/2025 of 23 January say "2024"; the citation date is used.
- **Signatures** are read from each law's text. Before 3 May 1993, laws were promulgated by the co-princes' permanent delegates or the veguers, or carry only the Síndic's signature.
- **Mentions** (the European Union and other bodies, currencies, articles of the Constitution) are counted in the text: a law counts if the name, acronym or number appears in it.
- **Partial periods** (2026, to 28 October, and the last term) are drawn lighter. 3 published laws enter into force after 29 October 2026 (branch `future`).

## Rebuilding

```sh
python visualisations/src/make.py            # git -> src/.build/ -> el-dret-andorra-en-20-grafics.html
node visualisations/src/stills.cjs           # images for these READMEs (needs Playwright; PLAYWRIGHT=<path> if not global)
```

`make.py` reads everything from git objects, so it also works in a blobless (`--filter=blob:none`) or `--no-checkout` clone, where it fetches the missing blobs of `lleis/` and `constitucio/` in batches (some 31,000 small files, about 25 MB) and the tables. It reads `origin/main` (or `HEAD`) and `origin/future` by default; `--ref` and `--future` pick others. It writes nothing into the repository except the page and the `src/.build/` folder (which git ignores).

| File | What it does |
| --- | --- |
| `src/make.py` | extracts the history, the trees, the tables and, for each law, the counts the charts use into `src/.build/`, then runs `prep.py` and `build.py` |
| `src/prep.py` | computes every number for the 20 charts and the data profile into `src/.build/data.json` |
| `src/page.tpl.html` | the page: text in both languages, the charts (d3), the tables |
| `src/build.py` | puts `data.json` into the template and writes the page |
| `src/stills.cjs` | draws each chart as a PNG into `stills/ca/` and `stills/en/` |

## Licence

See [`LICENSE`](../LICENSE). Official texts are not protected by copyright in Andorra (Llei sobre drets d'autor i drets veïns, del 10 de juny de 1999, article 4(2)), and the BOPA's legal notice allows reuse on the conditions quoted in `LICENSE`, one of which is that nothing suggests the BOPA Service takes part in, sponsors or supports it: this repository is not made, sponsored or endorsed by the Servei del Butlletí Oficial del Principat d'Andorra. The page, charts, tables and scripts in this folder are Lexifina's own contributions, CC0 1.0.
