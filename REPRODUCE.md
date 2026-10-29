# Reproduce this repository

Built 2026-10-29 from the BOPA documents retrieved 2026-10-29.

## Steps

How the documents were retrieved is not part of this record. With the retrieved manifest (`manifest.json`, the
list of documents under the themes "Lleis" and "Constitució") and documents (`docs/<folder>/<id>.html`, each matching
its sha256 in `data/source-sha256.tsv`) in the folder the scripts read (`CACHE` in manifest.py), and the retrieval
day in `fetched_on.txt`:

    cd tools/build
    python build.py <empty folder> --today 2026-10-29
    python check_words.py <that folder>   # letters and digits of every law against its BOPA document

The same documents give the same commit hashes: compare `data/source-sha256.tsv` with your own copy, then
`git rev-parse HEAD` (this build: see the commit you are reading) and `git rev-parse future`.

## Build scripts (sha256)

- manifest.py `aac72afdb4d773b92a1d5e2cec93c3f653ad4288582369c18094f03058805c40`
- parse.py `c5d87b6012e7a5c16c8a6b51632dae17ceff63653fd1ca26ef176f1ccffc6b6e`
- inforce.py `02ff612440f14fdfe5d8aa680ac3fa535b3d53f76e53f082aa968bd42ca4d9be`
- build.py `f83e273a269ffa9570ffda1c11d5632bb8e1d6f3e85ff2bfa23fbdb202b9a22b`
- docs.py `aeebc32ca74531ddec67e9477f9d1c1c4a9211088e5019a9e1ae9b31c7a210c8`
- check_words.py `b76b3ab266a3ec492b288b5eb7ee77702f16bf28f1b8bdfcaf19f84bdf6ddade`

Python 3.11 or later, standard library only; git 2.30 or later.

## What is decided where

- Which documents: everything under the themes "Lleis" and "Constitució" (the manifest); corrections of errata
  are listed in data/corrections.csv and not built (build.py `kind_of`).
- Where a law's text is: the whole document `<id>.html`, not the search's chunks (manifest.py `full_url`).
- Paragraphs: parse.py `reflow` (old printed lines joined back) and `Blocks` (HTML to lines; tables one row a line).
- Units: parse.py `units` (the longest run of article headings numbered 1, 2, 2 bis, 3..., which skips tables of
  contents and articles quoted from other laws).
- In-force dates: inforce.py `in_force`; the default rule and the time zone are in build.py and inforce.py.
- Folder names: build.py `load` (`lleis/<year>-<number>`; before numbering, `lleis/<publication date>-<document id>`).

## AI

The scripts, the README and these notes were written by Claude Code with Claude Opus 5.5 (`claude-opus-5-5`), working
for Lexifina. No AI model writes or changes legal text, and none runs when the repository is built or checked: the
build is the Python in `tools/build/`, run as recorded here.
