"""Hand-check helper: article files that also hold the law's additional, transitional, repealing or final provisions
(a heading line naming them inside an article-*.md file), i.e. provisions the build left in the last article's file.

    python -X utf8 tail_check.py <bare repo> <commit>
"""
import re, subprocess, sys

repo, pin = sys.argv[1], sys.argv[2]
ls = subprocess.run(["git", "-C", repo, "ls-tree", "-r", pin, "lleis", "constitucio"], capture_output=True, check=True).stdout.decode()
items = [(l.split("\t")[0].split()[2], l.split("\t")[1]) for l in ls.splitlines() if re.search(r"/article-[^/]*\.md$", l)]
cat = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
HEAD = re.compile(r"(?mi)^\s*(?:#+\s*)?(?:(?:Títol|Capítol)\s+[^\n]{0,40}?\.?\s*)?Disposici(?:ó|ons)\s+(?:addicional|transit[òo]ri|final|derogat[òo]ri)")
acts = {}
for sha, p in items:
    cat.stdin.write(sha.encode() + b"\n"); cat.stdin.flush()
    h = cat.stdout.readline().split()
    t = cat.stdout.read(int(h[2])).decode("utf-8", "replace"); cat.stdout.read(1)
    # skip quoted text of another law (amending laws quote whole provisions between « » or “ ”)
    if HEAD.search(t) and not re.search(r"[“«\"]", t[:t.find(HEAD.search(t).group(0))][-400:]):
        acts.setdefault(p.rsplit("/", 1)[0], []).append(p.rsplit("/", 1)[1])
for a, fs in sorted(acts.items()):
    print(a, ",".join(fs))
print("acts:", len(acts), file=sys.stderr)
