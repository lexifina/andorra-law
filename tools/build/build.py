"""Build the Andorra law repository (as enacted) from the BOPA cache (fetch.py).

    python scripts/andorra-law/build.py C:/Users/alany/Documents/andorra-law-build --today YYYY-MM-DD [--only REGEX]

The Butlletí Oficial del Principat d'Andorra (BOPA) publishes each law as enacted; there is no official consolidation
with dated past versions (Andorra makes consolidations as new laws, "de text consolidat", which come in here as laws
in their own right). So (shape 3 of NATIONAL-CURRENT-BRIEF, "as-enacted"):
1. Each law (and the Constitution) is one commit, authored by the law itself, holding its text as published: one file
   per article, disposition and annex, plus preamble.md (title, enacting words, statement of reasons) and
   signatures.md; one paragraph per line; index.txt lists the files in the law's order.
2. The commit is dated noon Andorra time on the day the law enters into force as its own final provisions say
   ("entra en vigor l'endemà de ser publicada", "al cap de vint dies", "l'1 de gener del 2023"), counted from the
   BOPA publication date. A law with no such clause is dated by the general rule (fifteen days after publication,
   Codi de l'Administració of 1989, article 9). The basis is the `In-force-basis:` trailer.
3. Amending laws are laws like any other. Their changes are NOT applied to the law they amend; each change they state
   ("Es modifica l'article 5 de la Llei 3/2010") is a row in data/amendments.csv. Corrections of errata are listed in
   data/corrections.csv and not applied.
4. Laws that enter into force after --today go on the branch `future` (never merged), on top of main.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
CACHE = HERE / '.cache'

from fetch import doc_path, full_url, unique_docs  # noqa: E402
from inforce import git_date, in_force, local_date  # noqa: E402
from parse import QUOTE, paragraphs, units  # noqa: E402

COMMITTER = 'Lexifina <andorra-law@lexifina.com>'
CODI_ADMIN = date(1989, 4, 13)  # Codi de l'Administració published (BOPA 1989 núm. 6); its art. 9 is the default rule
DEFAULT_DAYS = 15

NUMBERED = re.compile(r'^Llei(?:\s+qualificada)?\s+(\d{1,3})/((?:19|20)\d\d)\b', re.I)


def clean(s: str) -> str:
    s = urllib.parse.unquote_plus(s or '')
    s = re.sub(r'<[^>]+>', ' ', s)
    import html
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def title_of(d: dict, paras: list[tuple[str, str]]) -> str:
    for k, (cls, t) in enumerate(paras[:5]):
        if cls == 'Titol-3':
            if t in ('Llei', 'Llei qualificada', 'Edicte', 'Decret', 'Codi') and k + 1 < len(paras):
                return f'{t} {paras[k + 1][1]}'
            return t.rstrip(' .')
    s = clean(d['sumari'])
    if s and len(s) > 8:
        return s.rstrip(' .')
    # the old layout: "Llei" on one line, the rest of the title on the next
    lines = [t for _, t in paras[:3]]
    if lines and lines[0] in ('Llei', 'Llei qualificada') and len(lines) > 1:
        return f'{lines[0]} {lines[1]}'
    return lines[0] if lines else d['nomDocument']


def kind_of(title: str, d: dict) -> str:
    t = title.lower()
    if d.get('theme', '').startswith('Constituci') or t.startswith('constitució'):
        return 'constitution'
    if t.startswith(('correcció', 'correccio')):
        return 'correction'
    return 'law'


def sentences(ps: list[str]) -> list[str]:
    out = []
    for p in ps:
        if p.startswith(QUOTE):
            continue
        out += [s for s in re.split(r'(?<=[.;])\s+(?=[A-ZÀ-Ú])', p) if s]
    return out


def read_doc(d: dict) -> dict:
    p = doc_path(d)
    raw = p.read_bytes()
    paras, dropped = paragraphs(raw)
    us = units(paras)
    title = title_of(d, paras)
    published = local_date(d['dataPublicacioButlleti'])
    def body(kinds, word=''):
        return [l.lstrip('#').strip() for u in us if u['kind'] in kinds and word in u['stem'] for l in u['lines']
                if not l.startswith('## ')]
    finals, disps, arts = body(('disposition',), 'final'), body(('disposition',)), body(('article', 'annex'))
    pre = body(('preamble',))
    day, basis, quote = None, '', ''
    for group in (finals, disps, arts, pre):
        day, basis, quote = in_force(sentences(group), published)
        if day:
            break
    if day:
        basis_trailer = f'the law\'s own provision ({basis})'
    elif published >= CODI_ADMIN:
        day = published + timedelta(days=DEFAULT_DAYS)
        basis_trailer = 'general rule: fifteen days after publication (Codi de l\'Administracio, 1989, article 9); the law states no date'
        quote = ''
    else:
        day = published
        basis_trailer = 'publication date (the law states no date, and it predates the general rule)'
    return {'doc': d, 'title': title, 'kind': kind_of(title, d), 'published': published.isoformat(),
            'in_force': day.isoformat(), 'basis': basis_trailer, 'quote': quote, 'units': us, 'dropped': dropped,
            'sha256': hashlib.sha256(raw).hexdigest(), 'url': full_url(d), 'bytes': len(raw)}


# ---------------------------------------------------------------------------------------------------- amendments

LAW_REF = re.compile(r"(Llei(?:\s+qualificada)?\s+\d{1,3}/(?:19|20)\d\d"
                     r"|Llei(?:\s+qualificada)?\s+(?:de|del|d['’]|dels|sobre|general|per|reguladora|relativa)[^,;:]{3,160}?,\s+(?:de|del)\s+(?:l['’])?\d{1,2}(?:-\d{1,2}-\d{2,4}|\s+d[e’'][^,;:]{3,30}?(?:19|20)\d\d)"
                     r"|Constitució|Codi\s+(?:de|del|civil|penal)[^,;:.]{0,80})")
VERB = re.compile(r"\b(Es\s+modifica(?:n)?|Es\s+modifiquen|Queda(?:n)?\s+modificat(?:s|da|des)?|S['’]afegeix(?:en)?|S['’]addiciona(?:n)?|"
                  r"S['’]afegeixen|S['’]incorpora(?:n)?|S['’]introdueix(?:en)?|Es\s+deroga(?:n)?|Es\s+deroguen|Queda(?:n)?\s+derogat(?:s|da|des)?|"
                  r"Se\s+suprimeix(?:en)?|Es\s+suprimeix(?:en)?|Es\s+renumera(?:n)?|Es\s+renumeren)\b", re.I)
PROV = re.compile(r"(?:l['’]|els\s+|les\s+|la\s+|el\s+)?((?:article|articles|apartat|apartats|lletra|lletres|disposició|disposicions|annex|annexos|paràgraf|títol|capítol|secció)\b[^;:]{0,140}?)\s+(?:de\s+la|del|de\s+l['’]|a\s+la|al|a\s+l['’])\s*$", re.I)


def verb_kind(v: str) -> str:
    v = v.lower()
    if 'modifi' in v:
        return 'modification'
    if 'derog' in v or 'suprim' in v:
        return 'repeal'
    if 'renumer' in v:
        return 'renumbering'
    return 'insertion'


def amendment_rows(law: dict) -> list[list[str]]:
    rows = []
    for u in law['units']:
        if u['kind'] in ('preamble', 'signatures'):
            continue
        for para in u['lines']:
            if para.startswith(QUOTE) or para.startswith('#'):
                continue
            for m in VERB.finditer(para):
                tail = para[m.end():m.end() + 400]
                r = LAW_REF.search(tail)
                if not r or r.start() > 260:
                    continue
                before = tail[:r.start()]
                pm = PROV.search(before)
                prov = re.sub(r'\s+', ' ', pm.group(1)).strip() if pm else ''
                if not prov and not re.match(r'\s*(?:la|el)\s*$', before):
                    if re.search(r"\b(?:article|apartat|disposició|annex|lletra)\b", before, re.I):
                        prov = re.sub(r'\s+', ' ', before).strip(" ,'’")[:140]
                target = re.sub(r'\s+', ' ', r.group(1)).strip()
                target = re.sub(r'^(Llei(?: qualificada)? )0+(\d)', r'\1\2', target)
                if target.lower().startswith('llei') and law.get('number') and target.split()[-1] == law['number']:
                    continue
                rows.append([target, prov or '(whole)', verb_kind(m.group(1)), law['cite'], law['in_force'],
                             f"{law['dir']}/{u['stem']}.md", para[max(0, m.start() - 40):m.end() + 260]])
    return rows


# ---------------------------------------------------------------------------------------------------- catalogue

def load(only: str | None, today: str) -> tuple[list[dict], list[dict], list[list[str]]]:
    items = unique_docs(json.loads((CACHE / 'manifest.json').read_text('utf-8')))
    laws, corrections, issues = [], [], []
    for d in items:
        if only and not re.search(only, d['nomDocument'] + ' ' + clean(d['sumari'])):
            continue
        p = doc_path(d)
        if not p.exists():
            issues.append([d['nomDocument'], clean(d['sumari'])[:200], 'not fetched'])
            continue
        law = read_doc(d)
        if not any(u['lines'] for u in law['units']):
            issues.append([d['nomDocument'], law['title'][:200], 'no text in the HTML'])
            continue
        if law['kind'] == 'correction':
            corrections.append(law)
            continue
        laws.append(law)
    taken: dict[str, str] = {}
    for law in sorted(laws, key=lambda l: (l['published'], l['doc']['nomDocument'])):
        d = law['doc']
        m = NUMBERED.match(law['title'])
        law['number'] = f'{m.group(1)}/{m.group(2)}' if m else ''
        if law['kind'] == 'constitution':
            law['dir'] = 'constitucio'
            law['cite'] = "Constitució del Principat d'Andorra"
            law['email'] = 'constitucio-1993@bopa-ad.invalid'
        elif m:
            law['dir'] = f'lleis/{m.group(2)}-{int(m.group(1)):03d}'
            law['cite'] = f"Llei {law['number']}"
            law['email'] = f'llei-{m.group(2)}-{int(m.group(1))}@bopa-ad.invalid'
        else:
            law['dir'] = f"lleis/{law['published']}-{d['nomDocument'].lower()}"
            law['cite'] = re.sub(r'\s+', ' ', law['title'])[:100].rstrip(' ,.')
            law['email'] = f"doc-{d['nomDocument'].lower()}@bopa-ad.invalid"
        if law['dir'] in taken:
            issues.append([d['nomDocument'], law['title'][:200], f"number {law['number']} already used by {taken[law['dir']]}; built under its document id"])
            law['dir'] = f"{law['dir']}-{d['nomDocument'].lower()}"
            law['email'] = f"doc-{d['nomDocument'].lower()}@bopa-ad.invalid"
        taken[law['dir']] = d['nomDocument']
    for c in corrections:
        m = re.search(r'Llei(?:\s+qualificada)?\s+(\d{1,3})/((?:19|20)\d\d)', c['title'])
        c['target'] = f'lleis/{m.group(2)}-{int(m.group(1)):03d}' if m else ''
    laws.sort(key=lambda l: (l['in_force'], l['published'], l['dir']))
    for law in laws:
        law['future'] = law['in_force'] > today
    issues.sort()
    return laws, corrections, issues


# ---------------------------------------------------------------------------------------------------- write

def files_for(law: dict) -> dict[str, str]:
    files, order, seen = {}, [], set()
    for u in law['units']:
        if not u['lines']:
            continue
        name = f"{u['stem']}.md"
        assert name not in seen, (law['dir'], name)
        seen.add(name)
        files[f"{law['dir']}/{name}"] = '\n'.join(u['lines']) + '\n'
        order.append(name)
    files[f"{law['dir']}/index.txt"] = '\n'.join(order) + '\n'
    return files


def message(law: dict) -> tuple[str, str]:
    d = law['doc']
    title = re.sub(r'\s+', ' ', law['title']).strip()
    short = law['cite']
    subject = f"{short}: as enacted, in force {law['in_force']}"
    if len(subject) > 90:
        subject = f"{short[:70].rstrip(' ,')}...: as enacted"
    body = [f"{title}, as the Butlletí Oficial del Principat d'Andorra published it (núm. {d['numButlleti']}, "
            f"any {d['anyButlleti']}, {law['published']}), as enacted.", '']
    if law['quote']:
        body += [f"In force by its own words: \"{law['quote'][:400]}\"", '']
    else:
        body += [f"In force: {law['basis']}.", '']
    if law.get('amends'):
        body += [f"It states changes to {', '.join(sorted(law['amends'])[:8])}{' and others' if len(law['amends']) > 8 else ''}. "
                 "They are not applied to those laws' files here; they are listed in data/amendments.csv.", '']
    trailers = [f"In-force: {law['in_force']}", f"In-force-basis: {law['basis']}", 'Kind: enacted',
                f"Law: {title[:300]}", f"Published: {law['published']}",
                f"Bulletin: BOPA num. {d['numButlleti']} {d['anyButlleti']}{' (extra)' if d.get('isExtra') == 'True' else ''}",
                f"Source: {law['url']}", f"Source-sha256: {law['sha256']}"]
    msg = '\n'.join([subject, '', *body, *trailers]) + '\n'
    name = re.sub(r'[<>\n]', '', short)
    return f"{name} <{law['email']}>", msg.replace('\r', '')


class Writer:
    def __init__(self, repo: Path):
        self.p = subprocess.Popen(['git', '-C', str(repo), 'fast-import', '--quiet', '--force', '--done'],
                                  stdin=subprocess.PIPE)
        self.mark = 0

    def commit(self, ref: str, parent: int | None, author: str, when: str, msg: str, files: dict[str, bytes]) -> int:
        w = self.p.stdin.write
        self.mark += 1
        w(f'commit {ref}\nmark :{self.mark}\n'.encode())
        w(f'author {author} {when}\ncommitter {COMMITTER} {when}\n'.encode())
        m = msg.encode('utf-8')
        w(f'data {len(m)}\n'.encode() + m + b'\n')
        if parent:
            w(f'from :{parent}\n'.encode())
        for path, data in sorted(files.items()):
            w(f'M 100644 inline {path}\ndata {len(data)}\n'.encode() + data + b'\n')
        w(b'\n')
        return self.mark

    def finish(self) -> None:
        self.p.stdin.write(b'done\n')
        self.p.stdin.close()
        if self.p.wait():
            sys.exit('git fast-import failed')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('repo', type=Path)
    ap.add_argument('--today', required=True)
    ap.add_argument('--only')
    args = ap.parse_args()
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', args.today):
        sys.exit('--today must be YYYY-MM-DD')
    laws, corrections, issues = load(args.only, args.today)
    amend = []
    for law in laws:
        rows = amendment_rows(law)
        law['amends'] = {r[0] for r in rows}
        amend += rows
    amend.sort(key=lambda r: (r[4], r[3], r[5], r[0], r[1], r[2], r[6]))
    folders = {l['cite']: l['dir'] for l in laws}
    amend = [r[:1] + [folders.get(r[0], '')] + r[1:] for r in amend]
    main_laws = [l for l in laws if not l['future']]
    future = [l for l in laws if l['future']]
    nunits = sum(len([u for u in l['units'] if u['kind'] != 'preamble']) for l in laws)
    print(f"{len(laws)} laws ({len(future)} future), {nunits} units, {len(corrections)} corrections, "
          f"{len(issues)} issues, {len(amend)} amendment rows", flush=True)

    import docs as docmod
    docs = docmod.render(laws, corrections, issues, amend, args.today)

    repo = args.repo
    if repo.exists() and any(repo.iterdir()):
        mine = subprocess.run(['git', '-C', str(repo), 'log', '-1', '--format=%ce', 'HEAD'], capture_output=True, text=True).stdout.strip()
        if mine and mine != 'andorra-law@lexifina.com':
            sys.exit(f'{repo} holds something else; refusing to overwrite')
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / '.git').exists():
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
    for k, v in (('core.autocrlf', 'false'), ('core.longpaths', 'true')):
        subprocess.run(['git', '-C', str(repo), 'config', k, v], check=True)
    w = Writer(repo)
    parent = None
    for law in main_laws:
        author, msg = message(law)
        parent = w.commit('refs/heads/main', parent, author, git_date(law['in_force']), msg,
                          {k: v.encode('utf-8') for k, v in files_for(law).items()})
    fetched = (CACHE / 'fetched_on.txt').read_text().strip()
    msg = (f'Documentation: README, REPRODUCE, SOURCES, corpus.json, tools and data\n\n'
           f'Built from the BOPA (www.bopa.ad) as retrieved on {fetched}.\n\nIn-force: {args.today}\nKind: documentation\n')
    parent = w.commit('refs/heads/main', parent, COMMITTER, git_date(args.today), msg, docs)
    fparent = parent
    for law in future:
        author, msg = message(law)
        fparent = w.commit('refs/heads/future', fparent, author, git_date(law['in_force']), msg,
                           {k: v.encode('utf-8') for k, v in files_for(law).items()})
    if not future:
        subprocess.run(['git', '-C', str(repo), 'update-ref', '-d', 'refs/heads/future'], capture_output=True)
    w.finish()
    subprocess.run(['git', '-C', str(repo), 'checkout', '-q', '-f', 'main'], check=True)
    subprocess.run(['git', '-C', str(repo), 'clean', '-q', '-f', '-d'], check=True)
    head = subprocess.run(['git', '-C', str(repo), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    count = subprocess.run(['git', '-C', str(repo), 'rev-list', '--count', 'HEAD'], capture_output=True, text=True).stdout.strip()
    print(f'built {repo}: {count} commits on main, {len(future)} on future, head {head}', flush=True)


if __name__ == '__main__':
    main()
