"""Independent check of the Andorra repository against the BOPA documents: for every law commit (main and future),
the letters and digits of the law's files, in index.txt order, must equal the letters and digits of the BOPA document
it names (Source:, Source-sha256:), read here with a plain regex and not with the build's parser.

    python check_words.py ../andorra-law-build

Taken out of the document before comparing: the <head> and <title> (the document id), and the links the BOPA website adds ("Text refós",
"Descarrega el document"). Exit status 1 on any difference.
"""
import hashlib
import html
import re
import subprocess
import sys
from pathlib import Path

CACHE = Path(__file__).parent / '.cache' / 'docs'
SITE_LINK = re.compile(r'<a\b[^>]*>(?:(?!</a>).){0,200}?(?:Text refós|Descarrega el document)(?:(?!</a>).){0,200}?</a>', re.S | re.I)


def git(repo: str, *args: str) -> str:
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


class Blobs:
    """git cat-file --batch: one process for every file read."""

    def __init__(self, repo: str):
        self.p = subprocess.Popen(['git', '-C', repo, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def read(self, spec: str) -> str:
        self.p.stdin.write(spec.encode('utf-8') + b'\n')
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if len(head) < 3:
            raise KeyError(spec)
        data = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        return data.decode('utf-8')


def alnum(s: str) -> str:
    return ''.join(c for c in s if c.isalnum())


def source_text(raw: bytes) -> str:
    t = raw.decode('utf-16') if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else raw.decode('utf-8')
    t = re.sub(r'<head\b.*?</head>', ' ', t, flags=re.S | re.I)
    t = re.sub(r'<title\b.*?</title>', ' ', t, flags=re.S | re.I)
    t = SITE_LINK.sub(' ', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    return html.unescape(t)


def main() -> None:
    repo = sys.argv[1]
    refs = ['main'] + (['future'] if subprocess.run(['git', '-C', repo, 'rev-parse', '-q', '--verify', 'future'],
                                                     capture_output=True).returncode == 0 else [])
    seen = set()
    checked = bad = 0
    blobs = Blobs(repo)
    for ref in refs:
        log = git(repo, 'log', '--first-parent', '--format=%H%x1f%(trailers:key=Source,valueonly,separator=)%x1f'
                  '%(trailers:key=Source-sha256,valueonly,separator=)%x1e', ref)
        for rec in log.split('\x1e'):
            rec = rec.strip()
            if not rec:
                continue
            h, url, sha = (rec.split('\x1f') + ['', ''])[:3]
            if not url or h in seen:
                continue
            seen.add(h)
            folder, name = url.rsplit('/', 3)[-3], url.rsplit('/', 1)[-1]
            raw = (CACHE / folder / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != sha.strip():
                print(f'{h[:10]} {url}: cached document differs from Source-sha256')
                bad += 1
                continue
            changed = [p for p in git(repo, 'show', '--format=', '--name-only', h).split('\n') if p.endswith('index.txt')]
            law = changed[0].rsplit('/', 1)[0]
            names = [n for n in blobs.read(f'{h}:{law}/index.txt').splitlines() if n]
            ours = alnum(''.join(blobs.read(f'{h}:{law}/{n}') for n in names))
            theirs = alnum(source_text(raw))
            checked += 1
            if ours != theirs:
                bad += 1
                k = next((i for i, (a, b) in enumerate(zip(ours, theirs)) if a != b), min(len(ours), len(theirs)))
                print(f'{h[:10]} {law}: differs at {k} (ours {len(ours)}, source {len(theirs)}): '
                      f'ours ...{ours[max(0, k - 30):k + 30]}... source ...{theirs[max(0, k - 30):k + 30]}...')
    print(f'{checked} laws checked, {bad} differ')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
