"""Hand-check helper: rows of data/amendments.csv that modify or repeal an article of a law this repository holds
(amended_folder set) where that law, as enacted, has no file for the article. Also flags an amendment that takes effect
before the law it amends.

    python -X utf8 amend_check.py <amendments.csv> <tree listing (git ls-tree -r --name-only <pin> lleis constitucio)> <laws.csv>
"""
import csv, re, sys
from collections import defaultdict

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8")))
files = defaultdict(set)
for p in open(sys.argv[2], encoding="utf-8").read().split():
    folder, _, base = p.rpartition("/")
    files[folder].add(base[:-3] if base.endswith(".md") else base)
inforce = {}
for r in csv.DictReader(open(sys.argv[3], encoding="utf-8")):
    f = r.get("folder") or r.get("path") or ""
    inforce[f.rstrip("/")] = r.get("in_force") or r.get("in_force_date") or ""

ART = re.compile(r"(?:^|\bde l['’])article (\d{1,3})(?:\s?(bis|ter|quater|quinquies))?\b")
n = 0
for r in rows:
    f = r["amended_folder"].rstrip("/")
    if not f or r["kind"] not in ("modification", "repeal"):
        continue
    m = ART.search(r["provision"])
    if not m:
        continue
    num, suf = int(m.group(1)), m.group(2)
    want = f"article-{num:03d}" + (f"-{suf}" if suf else "")
    have = files.get(f, set())
    if not have:
        continue
    if want not in have and not (num == 1 and "article-unic" in have):
        arts = sorted(int(x[8:11]) for x in have if re.match(r"article-\d{3}$", x))
        n += 1
        print(f"{f}\t{r['provision']}\t{r['kind']}\t{r['amending_in_force']}\t{r['file']}\tmax={arts[-1] if arts else None}\t{r['sentence'][:220]}")
print("rows:", n, file=sys.stderr)
