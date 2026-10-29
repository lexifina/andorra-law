"""README, REPRODUCE.md, SOURCES.md, LICENSE, corpus.json, laws.csv, data/ and tools for the Andorra law repository
(called by build.py)."""
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
REPO_FILES = HERE / 'repo'
CACHE = HERE / '.cache'
BUILD_FILES = ('fetch.py', 'parse.py', 'inforce.py', 'build.py', 'docs.py', 'check_words.py')
TEMPLATES = ('README.md', 'REPRODUCE.md', 'SOURCES.md', 'LICENSE', 'tools/in_force_on.py')


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _csv(rows: list[list]) -> bytes:
    out = io.StringIO()
    w = csv.writer(out, lineterminator='\n')
    for r in rows:
        w.writerow(r)
    return out.getvalue().encode('utf-8')


def render(laws: list[dict], corrections: list[dict], issues: list[list[str]], amend: list[list[str]],
           today: str) -> dict[str, bytes]:
    main = [l for l in laws if not l['future']]
    future = [l for l in laws if l['future']]
    basis = Counter('own' if l['basis'].startswith("the law's own") else
                    'default' if l['basis'].startswith('general rule') else 'publication' for l in laws)
    units = sum(1 for l in laws for u in l['units'] if u['kind'] != 'preamble')
    copyright_dir = next((l['dir'] for l in laws if l['doc']['nomDocument'] == '198BE'), 'lleis/1999-07-06-198be')
    codi_dir = next((l['dir'] for l in laws if l['doc']['nomDocument'] == '14772'), 'lleis/1989-04-09-14772')
    fetched = (CACHE / 'fetched_on.txt').read_text().strip()
    manifest = json.loads((CACHE / 'manifest.json').read_text('utf-8'))
    import fetch
    documents = len(fetch.unique_docs(manifest))
    stats = {
        'today': today, 'fetched': fetched, 'documents': documents, 'laws': len(laws) - 1, 'laws_all': len(laws),
        'units': units, 'commits_main': len(main) + 1, 'law_commits': len(main), 'future': len(future),
        'first': min(l['in_force'] for l in main), 'last': max(l['in_force'] for l in main),
        'first_published': min(l['published'] for l in laws), 'last_published': max(l['published'] for l in laws),
        'basis_own': basis['own'], 'basis_default': basis['default'], 'basis_publication': basis['publication'],
        'amendment_rows': len(amend), 'corrections': len(corrections), 'unreadable': len(issues),
        'copyright_dir': copyright_dir, 'codi_dir': codi_dir,
        'by_year': dict(sorted(Counter(l['in_force'][:4] for l in laws).items())),
    }

    def fill(t: str) -> str:
        for k, v in stats.items():
            if isinstance(v, (str, int)):
                t = t.replace('{{' + k.upper() + '}}', str(v))
        for name in BUILD_FILES:
            t = t.replace('{{SHA_' + name.upper().replace('.', '_') + '}}', _sha((HERE / name).read_bytes()))
        return t

    laws_csv = _csv([['folder', 'citation', 'title', 'published', 'bulletin', 'in_force', 'in_force_basis', 'branch',
                      'units', 'document', 'source']] +
                    [[l['dir'], l['cite'], l['title'], l['published'], f"{l['doc']['numButlleti']}/{l['doc']['anyButlleti']}",
                      l['in_force'], l['basis'], 'future' if l['future'] else 'main',
                      sum(1 for u in l['units'] if u['kind'] != 'preamble'), l['doc']['nomDocument'], l['url']]
                     for l in sorted(laws, key=lambda l: (l['published'], l['dir']))])
    amend_csv = _csv([['amended_law', 'amended_folder', 'provision', 'kind', 'amending_law', 'amending_in_force', 'file', 'sentence']] + amend)
    corr_csv = _csv([['title', 'published', 'bulletin', 'corrects_folder', 'document', 'source', 'source_sha256']] +
                    [[c['title'], c['published'], f"{c['doc']['numButlleti']}/{c['doc']['anyButlleti']}", c['target'],
                      c['doc']['nomDocument'], c['url'], c['sha256']] for c in sorted(corrections, key=lambda c: c['published'])])
    issues_csv = _csv([['document', 'title', 'issue']] + issues)
    sums = ''.join(f"{l['url'].rsplit('/', 3)[-3]}/{l['url'].rsplit('/', 1)[-1]}\t{l['sha256']}\n"
                   for l in sorted(laws + corrections, key=lambda l: l['url']))

    corpus = {
        'corpus': 'ad/national/acts',
        'name': "Laws of Andorra (the Constitution and the laws of the Consell General), as enacted",
        'label': 'Andorra',
        'language': 'ca',
        'history': 'as-enacted',
        'history_from': stats['first'],
        'record_to': stats['last'],
        'record_note': (f"{len(laws)} texts from the Butlletí Oficial del Principat d'Andorra (the Constitution and "
                        f"{len(laws) - 1} laws, published {stats['first_published']} to {stats['last_published']}), each "
                        'as enacted, dated by its entry into force; amendments are not applied (they are listed in '
                        f'data/amendments.csv). Retrieved {fetched}, built {today}.'),
        'built': today,
        'in_force_trailer': 'In-force',
        'has_future_branch': bool(future),
        'future_branch': 'future',
        'laws': {'constitution': 1, 'laws': len(laws) - 1},
        'dates': {'commit': "in-force (the law's own entry-into-force provision, counted from its BOPA publication "
                            "date; else fifteen days after publication, Codi de l'Administracio 1989 art. 9)",
                  'other_trailers': ['In-force-basis', 'Published'], 'time': '12:00 Europe/Andorra (CET/CEST)',
                  'before_1970': 'none (the record starts in 1989)', 'future': 'branch future, never merged'},
        'author': {'enacted': 'the law itself', 'amendment': 'none: amendments are not applied'},
        'scope': {
            'trailer': 'Applies',
            'groups': 'any one line',
            'conditions': 'all of a line',
            'when_absent': 'not extracted for Andorra; transitional provisions are in each law',
            'default_reach': {
                'rule': 'no retroactivity of restrictive provisions',
                'meaning': 'the Constitution guarantees the principle of the non-retroactivity of provisions that '
                           'restrict individual rights or that impose a penalty; otherwise a law applies from its '
                           'entry into force unless it says so',
                'authority': "Constitució del Principat d'Andorra (1993), article 3.2",
                'decided_here': False,
            },
        },
        'citation': {'file': r'((?:constitucio|lleis/[^/]+))/article-0*([0-9]+)(?:-[a-z]+)?\.md',
                     'cites': r'(^|[^[:alnum:]])[Aa]rticles? {n}([^0-9]|$)',
                     'note': 'article numbers within the same law ("article 25", "articles 25 i 26" match only the '
                             'first); a later law\'s reference to an article of another law is not resolved'},
        'tool': 'tools/in_force_on.py',
    }

    files = {
        'corpus.json': (json.dumps(corpus, indent=2, ensure_ascii=False) + '\n').encode('utf-8'),
        'laws.csv': laws_csv,
        'data/amendments.csv': amend_csv,
        'data/corrections.csv': corr_csv,
        'data/unreadable.csv': issues_csv,
        'data/stats.json': (json.dumps(stats, indent=1, sort_keys=True, ensure_ascii=False) + '\n').encode('utf-8'),
        'data/source-sha256.tsv': sums.encode('utf-8'),
    }
    for name in TEMPLATES:
        b = (REPO_FILES / name).read_bytes()
        files[name] = fill(b.decode('utf-8')).encode('utf-8') if name.endswith('.md') else b
        files[f'tools/build/repo/{name}'] = b
    for name in BUILD_FILES:
        files[f'tools/build/{name}'] = (HERE / name).read_bytes()
    return files
