"""Hand-check helper: acts whose article files do not run 1..N (first file above 1, or numbers missing between), and,
for each, whether the missing articles' headings ("Article 3", "Article 3. ...") appear in another file of the act
(preamble.md or a neighbouring article), i.e. text the build left inside another file.

    python -X utf8 gap_check.py <bare repo> <commit>
"""
import re, subprocess, sys
from collections import defaultdict

repo, pin = sys.argv[1], sys.argv[2]
ls = subprocess.run(["git", "-C", repo, "ls-tree", "-r", pin, "lleis", "constitucio"], capture_output=True, check=True).stdout.decode()
acts = defaultdict(dict)
for l in ls.splitlines():
    meta, p = l.split("\t")
    f, _, b = p.rpartition("/")
    acts[f][b] = meta.split()[2]


def show(sha):
    return subprocess.run(["git", "-C", repo, "cat-file", "-p", sha], capture_output=True).stdout.decode("utf-8", "replace")


n = 0
for f, files in sorted(acts.items()):
    nums = sorted({int(m.group(1)) for b in files for m in [re.match(r"article-(\d{3})\.md$", b)] if m})
    if not nums or "article-unic.md" in files:
        continue
    missing = [i for i in range(1, nums[-1] + 1) if i not in nums]
    if not missing:
        continue
    found = defaultdict(list)
    for b, sha in files.items():
        if not b.endswith(".md"):
            continue
        t = show(sha)
        for m in re.finditer(r"(?m)^\s*(?:#+\s*)?Articles?\s+(\d{1,3})\b(?!\s*(?:bis|ter|quater|\.\d))", t):
            k = int(m.group(1))
            if k in missing:
                found[k].append(b)
    inside = sorted(found)
    n += 1
    where = sorted({b for v in found.values() for b in v})
    print(f"{f}\tfiles {nums[0]}..{nums[-1]} ({len(nums)})\tmissing {len(missing)}: {missing[:12]}{'...' if len(missing) > 12 else ''}"
          f"\theadings found for {len(inside)} in {where[:4]}")
print("acts:", n, file=sys.stderr)
