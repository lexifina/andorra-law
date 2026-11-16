# Tools

The scripts behind this Andorra-only run of global-law's vulnerability detectors. They run inside a copy of
[global-law/vulnerabilities/scripts](https://github.com/lexifina/global-law/tree/main/vulnerabilities/scripts) (Python 3.11+,
`pip install duckdb pyarrow`), with a bare clone of this repository at `sources/corpus/andorra-law.git`, a blobless bare
clone of global-law at `sources/global-law.git`, and a `pins.json` that names only andorra-law and its commit.
`build_vulns.py`, `flags_chart.py`, `late_ext_select.py`, `late_ext_rebut.py` and `patch_ca.py` sit two folders above the
scripts, next to `config.json`.

| Script | What it does |
| --- | --- |
| `run.sh` | Applies `patch_ca.py`, indexes the history and texts, adds this repository's history rows, and runs the detectors (`bash run.sh <shards>`) |
| `add_root.py` | Builds the history rows from this repository's own commits (global-law replays it only up to an earlier commit), so the detectors read every law |
| `patch_ca.py` | The Catalan fixes below, in the copy of global-law's scripts (`python -X utf8 patch_ca.py <scripts dir>`; a fix already in place is skipped) |
| `run_triage.sh` | The model review: the 40 strongest flags per category, the 40 strongest lapsed time limits in law texts, and the empty periods |
| `late_ext_select.py` | Chooses the empty periods for global-law's review of that category (there were none here) |
| `late_ext_rebut.py` | Adds the second, arguing-against pass to the empty-period review, as `triage.py` does for the other categories |
| `build_vulns.py` | Builds `data/flags.csv`, `data/reviewed.csv` and `data/by_category.csv` from the findings and the model review |
| `flags_chart.py` | Draws the chart at the top of the READMEs, in Catalan and English, light and dark |
| `config.json` | The repository, the Catalan category names, the files that are not law, and the chart's labels |
| `patch_detectors.py` | Fixes blind spots found in runs on several country repositories in the copy of global-law's scripts (`python -X utf8 patch_detectors.py <scripts dir>`; a fix already in place is skipped) |
| `patch_detectors_vi.py` | The same for Vietnamese dates, references and amounts (found by the Vietnam run); it changes nothing here, but `redo.py` runs it on every repository |
| `patch_es.py` | The same for Spanish dates and for "marco" and "escudo" read as currencies; it changes nothing here either |
| `map_moved.py` | Rewrites the paths in the history table for repositories that moved their act folders (`data/paths.json`); this repository has not, so it does nothing here |
| `redo.py` | Runs `patch_detectors.py`, `patch_detectors_vi.py` and `patch_es.py`, then again only the scans and detectors the fixes change, the model review of lapsed time limits, references to deleted provisions and empty periods, and the build (`python -X utf8 redo.py <run folder> [--keep-reviews] [--full]`; `EMBED_FONTS` names the script that embeds the chart's fonts). It does not run `patch_ca.py`, and `--full` puts global-law's `run.sh` back; run `patch_ca.py` first |
| `amend_check.py` | Hand-check helper: the rows of `data/amendments.csv` that amend or repeal an article for which the amended law's folder has no file |
| `gap_check.py` | Hand-check helper: the laws whose article files do not run from Article 1 without gaps, and where the missing articles' headings are |
| `tail_check.py` | Hand-check helper: the article files that also hold additional, transitional, repealing or final provisions |

The model review needs `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL` and `LLM_AUTH` set for an OpenAI-compatible Responses API.
It was run as `bash run_triage.sh '^(data/|tools/|README|REPRODUCE|SOURCES|LICENSE|corpus\.json|laws\.csv)'`; every law is
under `lleis/` or `constitucio/`, so the review of lapsed time limits in law texts drew the same 40 flags as the review of
all of them.

The detectors in this copy already carry every fix of `patch_detectors.py`. Changes made for this repository:

- `add_root.py` counts `Kind: enacted`, which this repository gives every law, as law. Without it the first run had no
  rows of kind `law`: the reference scan read no file (`blobs=0`) and the history detectors had nothing to read. The documentation
  and tools commit (`Kind: documentation`) is still left out.
- `patch_ca.py`, Catalan dates: the time-limit search now knows the Catalan month names, "d'agost" and the like (d' before
  the month), "fins al", "fins a l'" and "fins el", and the deadlines "abans del", "no més tard del", "com a màxim" and
  "com a molt tard" (read as deadlines, like "not later than"). Lapsed time limits went from 2 to 224.
- `patch_ca.py`, currencies: the Catalan peseta ("pessetes", "pesseta") is now a dead currency, and "sucre" (sugar, in a
  customs tariff's "Sucre 1%") is no longer read as the Ecuadorian sucre in Catalan. Dead currencies went from 7 to 329.
- `run.sh` runs `patch_ca.py` first.

The reference scan reads Catalan references ("article 12", "l'apartat 2 de l'article 5", "els articles 3, 7 i 12 a 14");
it also reads "l'article 12 de la Llei 10/2008" as article 12 of the citing law. That does no harm here, since each law has
only its text as enacted and no article disappears, but a run on a history with deleted articles would need Catalan act
names ("de la Llei", "del Codi") in the detector's list of other acts.
