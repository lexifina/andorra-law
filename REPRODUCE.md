# Reproduce this repository

Built 2026-10-29 from the BOPA documents retrieved 2026-10-29.

## Steps

    git clone https://github.com/lexifina/lexifina   # or copy tools/build/ from this repository
    cd scripts/andorra-law
    python fetch.py manifest        # the list of documents: one search per theme and year (about 3 minutes)
    python fetch.py docs            # every document's whole HTML, one request at a time (about 40 minutes)
    python build.py <empty folder> --today 2026-10-29
    python check_words.py <that folder>   # letters and digits of every law against its BOPA document

The same documents give the same commit hashes: compare `data/source-sha256.tsv` with your own cache, then
`git rev-parse HEAD` (this build: see the commit you are reading) and `git rev-parse future`.

## Fetch rate

One request at a time to each host, about one a second; every answer is cached (errors for a day). The BOPA's
robots.txt disallows nothing; the document store has none.

## Build scripts (sha256)

- fetch.py `9876459f8ff5e05934a033e3a493158c8f5ee0a125a6b84ba740fb2c8ef2fa4e`
- parse.py `c5d87b6012e7a5c16c8a6b51632dae17ceff63653fd1ca26ef176f1ccffc6b6e`
- inforce.py `02ff612440f14fdfe5d8aa680ac3fa535b3d53f76e53f082aa968bd42ca4d9be`
- build.py `e5a1d8f591dce474ad9ed7452d1528ac03c212f8f87307f559b966cf21d7962b`
- docs.py `495c55a654b8dba669fe97fd33394776de25088e8a6c18fe6f2a8d976bdf671a`
- check_words.py `11b153b12c1447c93211858e07928bf1d3fce6255d40ec3e4e0c1f11122ac969`

Python 3.11 or later, standard library only; git 2.30 or later.

## What is decided where

- Which documents: everything under the themes "Lleis" and "Constitució" (fetch.py `THEMES`); corrections of errata
  are listed in data/corrections.csv and not built (build.py `kind_of`).
- Where a law's text is: the whole document `<id>.html`, not the search's chunks (fetch.py `full_url`).
- Paragraphs: parse.py `reflow` (old printed lines joined back) and `Blocks` (HTML to lines; tables one row a line).
- Units: parse.py `units` (the longest run of article headings numbered 1, 2, 2 bis, 3..., which skips tables of
  contents and articles quoted from other laws).
- In-force dates: inforce.py `in_force`; the default rule and the time zone are in build.py and inforce.py.
- Folder names: build.py `load` (`lleis/<year>-<number>`; before numbering, `lleis/<publication date>-<document id>`).
