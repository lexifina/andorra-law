"""Rebuild visualisations/el-dret-andorra-en-20-grafics.html from this repository.

    python visualisations/src/make.py [--repo PATH] [--ref REF] [--future REF] [--skip-extract]

Steps (all read-only on the repository; scratch output goes to visualisations/src/.build/):
  1. git log of REF (default origin/main) and of FUTURE (default origin/future, the laws that enter into force
     later), streamed: one line per commit with its author (the law itself), its trailers (In-force, In-force-basis,
     Kind, Law, Published, Bulletin, Source) and the entry-into-force sentence the message quotes  -> .build/log.tsv
  2. the tables of REF: laws.csv, corpus.json, data/stats.json, data/amendments.csv, data/corrections.csv,
     data/unreadable.csv                                                                              -> .build/repo/
  3. the trees of REF and FUTURE under lleis/ and constitucio/: every file of every law, with its blob id
  4. every file of every law and of the Constitution, read one blob at a time; for each law only counts are kept
     (files and words by kind of unit, headings, the session date of the preamble, the signatures, mentions of EU
     law, international bodies, currencies, parishes and articles of the Constitution)               -> .build/laws.jsonl
     the Constitution's articles (number, heading, words)                                           -> .build/constitution.jsonl
  5. prep.py turns those into .build/data.json; build.py fills page.tpl.html with it.
In a partial (blobless) clone the missing blobs are fetched in batches (about 31,000 small files, some 25 MB);
nothing large is held in memory.
"""
import argparse, json, os, re, subprocess, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--repo', default=os.path.abspath(os.path.join(HERE, '..', '..')))
ap.add_argument('--ref', default=None, help='default: origin/main if present, else HEAD')
ap.add_argument('--future', default=None, help='default: origin/future if present (the laws in force later)')
ap.add_argument('--out', default=os.path.join(HERE, '..', 'el-dret-andorra-en-20-grafics.html'))
ap.add_argument('--skip-extract', action='store_true', help='reuse .build/ from a previous run (prep and build only)')
ap.add_argument('--extract-only', action='store_true', help='stop after the extraction into .build/')
a = ap.parse_args()
B = os.path.join(HERE, '.build')
os.makedirs(os.path.join(B, 'repo'), exist_ok=True)
NOLAZY = dict(os.environ, GIT_NO_LAZY_FETCH='1')
GIT = ['git', '-C', a.repo, '-c', 'core.quotepath=off']


def git(*args):
    return subprocess.run([*GIT, *args], check=True, capture_output=True, env=NOLAZY).stdout


def has(ref):
    return subprocess.run([*GIT, 'rev-parse', '--verify', '-q', ref], capture_output=True).returncode == 0


ref = a.ref or ('origin/main' if has('origin/main') else 'HEAD')
fut = a.future if a.future is not None else ('origin/future' if has('origin/future') else '')
sha = git('rev-parse', ref).decode().strip()
fsha = git('rev-parse', fut).decode().strip() if fut else ''
print('ref', ref, sha, '| future', fut or '-', fsha, flush=True)

TRAILERS = ['In-force', 'In-force-basis', 'Kind', 'Law', 'Published', 'Bulletin', 'Source']
QUOTE = re.compile(r'^In force by its own words: "(.*)"\s*$')


def fetch_missing(oids, batch=8000):
    """batched fetches for the blobs a partial clone does not have yet (never one at a time)"""
    oids = sorted(set(oids))
    chk = subprocess.run([*GIT, 'cat-file', '--batch-check'], input=''.join(o + '\n' for o in oids).encode(),
                         capture_output=True, env=NOLAZY).stdout.decode().split('\n')
    missing = [l.split()[0] for l in chk if l.endswith(' missing')]
    for i in range(0, len(missing), batch):
        part = missing[i:i + batch]
        print('fetching', len(part), 'blobs', f'({i + len(part)} of {len(missing)})', flush=True)
        subprocess.run([*GIT, '-c', 'fetch.negotiationAlgorithm=noop', 'fetch', 'origin', '--no-tags', '--no-write-fetch-head',
                        '--recurse-submodules=no', '--filter=blob:none', '--stdin'], input=''.join(m + '\n' for m in part).encode(),
                       check=False, env=NOLAZY)


def read_blobs(items):
    """yield (key, text) for (oid, key) pairs, one blob at a time"""
    p = subprocess.Popen([*GIT, 'cat-file', '--batch'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, env=NOLAZY)
    for oid, key in items:
        p.stdin.write((oid + '\n').encode()); p.stdin.flush()
        head = p.stdout.readline().split()
        if len(head) < 3:
            sys.exit('cannot read ' + str(key))
        data = p.stdout.read(int(head[2])); p.stdout.read(1)
        yield key, data.decode('utf-8', 'replace')
    p.stdin.close(); p.wait()


def tree(r, *paths):
    """(path, oid) of every file of the tree of r under paths, streamed"""
    lt = subprocess.Popen([*GIT, 'ls-tree', '-r', '-z', r, '--', *paths], stdout=subprocess.PIPE, env=NOLAZY)
    buf = b''
    for chunk in iter(lambda: lt.stdout.read(1 << 16), b''):
        buf += chunk
        *ents, buf = buf.split(b'\0')
        for e in ents:
            meta, path = e.split(b'\t', 1)
            yield path.decode('utf-8'), meta.split()[2].decode()
    lt.wait()


# ------------------------------------------------------------------ the text measures
WCH = re.compile(r'\w')


def words(text):
    """words: the whitespace-separated tokens that hold a letter or a digit (linear, whatever the line length)"""
    return sum(1 for t in text.split() if WCH.search(t))


MES = ['gener', 'febrer', 'març', 'abril', 'maig', 'juny', 'juliol', 'agost', 'setembre', 'octubre', 'novembre', 'desembre']
DATE_TXT = re.compile(r"(\d{1,2})\s+(?:de\s+|d['’]\s*)(" + '|'.join(MES) + r")\s+(?:de[l]?\s+)?(\d{4})", re.I)
SESSION = re.compile(r"sessi[óo]\s+(?:\w+\s+){0,3}?(?:del?s?\s+)?(?:dia|dies)\s+(.{3,90}?)\s+(?:ha|han)\s+aprovat", re.I)
NUMS = {'u': 1, 'un': 1, 'dos': 2, 'tres': 3, 'quatre': 4, 'cinc': 5, 'sis': 6, 'set': 7, 'vuit': 8, 'nou': 9, 'deu': 10, 'onze': 11,
        'dotze': 12, 'tretze': 13, 'catorze': 14, 'quinze': 15, 'setze': 16, 'disset': 17, 'divuit': 18, 'dinou': 19, 'vint': 20,
        'vint-i-u': 21, 'vint-i-un': 21, 'vint-i-dos': 22, 'vint-i-tres': 23, 'vint-i-quatre': 24, 'vint-i-cinc': 25, 'vint-i-sis': 26,
        'vint-i-set': 27, 'vint-i-vuit': 28, 'vint-i-nou': 29, 'trenta': 30, 'trenta-u': 31, 'trenta-un': 31}
FR = {'Mitterrand': 'mitterrand', 'Chirac': 'chirac', 'Sarkozy': 'sarkozy', 'Hollande': 'hollande', 'Macron': 'macron'}
EP = {'Alan': 'marti', 'Vives': 'vives', 'Serrano': 'serrano'}
SIND = re.compile(r'^(?:El |La )?(Síndica? General|Subsíndica? General|Sub-Síndic General)$')
# mentions: (key, regex) counted per law over every file but the signatures
MENTION = [
    ('eu', r"\bUni[óo] Europea\b"),
    ('ec', r"\bComunitat(?:s)? Econ[òo]mica Europea\b|\bComunitat Europea\b|\bComunitats Europees\b"),
    ('dir', r"\bDirectiv(?:a|es)\s+(?:\((?:UE|CE|CEE|Euratom)\)\s*)?(?:del Consell\s+)?(?:n[úu]m\.\s*)?\d{1,4}/\d{1,4}"),
    ('reg', r"\bReglament\s+(?:delegat\s+|d['’]execuci[óo]\s+)?\((?:UE|CE|CEE)\)"),
    ('monetari', r"\bAcord [Mm]onetari\b"),
    ('assoc', r"\bAcord d['’][Aa]ssociaci[óo]\b"),
    ('ocde', r"\bOCDE\b|\bOrganitzaci[óo] per a la Cooperaci[óo] i el Desenvolupament Econ[òo]mics\b"),
    ('coe', r"\bConsell d['’]Europa\b"),
    ('gafi', r"\bGAFI\b|\bGrup d['’]Acci[óo] Financera\b"),
    ('moneyval', r"\bMONEYVAL\b|\bMoneyval\b"),
    ('onu', r"\bNacions Unides\b"),
    ('pta', r"\bpessetes\b|\bpesseta\b|\bPTA\b|\bptes\.?(?=\s)"),
    ('frf', r"\bfrancs francesos\b|\bfranc francès\b|\bFF\b"),
    ('eur', r"\beuros?\b|€"),
    ('ecu', r"\bECU\b|\becus\b"),
    ('consolidat', r"\btext consolidat\b"),
]
MENTION = [(k, re.compile(rx)) for k, rx in MENTION]
DIRNUM = re.compile(r"\bDirectiv(?:a|es)\s+(?:\((?:UE|CE|CEE|Euratom)\)\s*)?(?:del Consell\s+)?(?:n[úu]m\.\s*)?(\d{1,4}/\d{1,4})")
PARISH = [('canillo', r"\bCanillo\b"), ('encamp', r"\bEncamp\b"), ('ordino', r"\bOrdino\b"), ('massana', r"\bLa Massana\b|\bla Massana\b"),
          ('andorra', r"\bAndorra la Vella\b"), ('julia', r"\bSant Juli[àa] de L[òo]ria\b"), ('escaldes', r"\bEscaldes(?:-|\s)Engordany\b")]
PARISH = [(k, re.compile(rx)) for k, rx in PARISH]
CNUM = r"\d{1,3}(?:\.\d{1,2})*(?:\s?[a-z]\))?"
CONST = re.compile(r"\barticles?\s+(" + CNUM + r"(?:(?:,\s*|\s+i\s+|\s+o\s+|\s*-\s*)" + CNUM + r")*)\s+de la Constituci[óo]\b", re.I)
HEAD = re.compile(r'^#{1,3}\s*(Llibre|T[íi]tol|Cap[íi]tol|Secci[óo]|Subsecci[óo])\b', re.I)
PRESENT = [('la_present', re.compile(r"\bLa present Llei\b")), ('aquesta', re.compile(r"\bAquesta Llei\b"))]


def kind_of(name):
    n = name[:-3] if name.endswith('.md') else name
    if n.startswith('article'):
        return 'art'
    for k, p in (('add', 'disposicio-addicional'), ('trans', 'disposicio-transitoria'), ('derog', 'disposicio-derogatoria'), ('final', 'disposicio-final')):
        if n.startswith(p):
            return k
    if n.startswith('annex'):
        return 'annex'
    return {'preamble': 'pre', 'signatures': 'sig', 'index.txt': 'idx'}.get(n, 'other')


def date_iso(d, m, y):
    return f'{int(y):04d}-{int(m):02d}-{int(d):02d}'


def first_date(s):
    m = DATE_TXT.search(s)
    if m:
        return date_iso(m.group(1), MES.index(m.group(2).lower()) + 1, m.group(3))
    return None


def word_date(s):
    """'el vint-i-nou de març de mil nou-cents vuitanta-nou' -> 1989-03-29 (the pre-1993 promulgations)"""
    s = s.lower().replace('’', "'")
    m = re.search(r"(?:el |als )?([a-z-]+) (?:de |d')(" + '|'.join(MES) + r") (?:del? )?mil nou-cents ([a-z-]+)", s)
    if not m or m.group(1) not in NUMS:
        return None
    tens = {'vuitanta': 80, 'noranta': 90}
    t = m.group(3).split('-')
    if t[0] not in tens:
        return None
    y = 1900 + tens[t[0]] + (NUMS.get('-'.join(t[1:]), 0) if len(t) > 1 else 0)
    return date_iso(NUMS[m.group(1)], MES.index(m.group(2)) + 1, y)


def session_date(pre):
    """the last day of the Consell General session the preamble names ('en la seva sessió del dia 6 de desembre del 2018')"""
    m = SESSION.search(pre.replace('\n', ' '))
    if not m:
        return None, None
    span = m.group(1)
    ds = list(DATE_TXT.finditer(span))
    if ds:
        d = ds[-1]
        # 'dels dies 2 i 3 de setembre de 1993': the last day named
        days = re.findall(r'\b(\d{1,2})\b', span[:d.start()] + d.group(1))
        last = max(int(x) for x in days) if days else int(d.group(1))
        return date_iso(last, MES.index(d.group(2).lower()) + 1, d.group(3)), span.strip()
    return None, span.strip()


def signatures(sig):
    lines = [l.strip() for l in sig.split('\n') if l.strip()]
    out = {'place': None, 'date': None, 'sindic': None, 'role': None, 'fr': None, 'ep': None, 'pre': None}
    if not lines:
        return out
    first = lines[0].lstrip('#').strip()
    pl = first.split(',')[0].strip()
    out['place'] = pl[:60]
    out['date'] = first_date(first) or word_date(first)
    # only the head of the block: budget laws carry their tables after the signatures
    head = []
    for l in lines[1:30]:
        if re.match(r'^(Pressupost|Quadres?|Classificaci|Annex|\d+\s*\|)', l):
            break
        head.append(l)
    txt = ' | '.join(head)
    for i, l in enumerate(head):
        m = SIND.match(l)
        if m:
            out['role'] = m.group(1).replace('Sub-Síndic', 'Subsíndic')
            prev = head[i - 1] if i else ''
            if prev and not prev.startswith('#') and not SIND.match(prev) and len(prev) < 60 and not re.search(r'\d', prev):
                out['sindic'] = prev
            break
        m2 = re.match(r'^(?:El |La )?(Síndica? General|Subsíndica? General|Sub-Síndic General)\b', l)
        if m2:   # 'El Síndic General 9 | Pressupost ...': no name printed
            out['role'] = m2.group(1).replace('Sub-Síndic', 'Subsíndic')
            break
    for k, v in FR.items():
        if k in txt:
            out['fr'] = v
    for k, v in EP.items():
        if k in txt:
            out['ep'] = v
    if 'Delegat Permanent' in txt:
        out['pre'] = 'delegats'
    elif 'Veguer' in txt:
        out['pre'] = 'veguers'
    return out


def measure(folder, files):
    """files: [(name, text)] of one law -> its record (counts only)"""
    r = {'f': folder, 'n': Counter(), 'w': Counter(), 'h': Counter(), 'm': Counter(), 'par': Counter(), 'const': Counter(),
         'dirs': [], 'pres': Counter()}
    pre = sig = ''
    for name, text in files:
        k = kind_of(name)
        if k == 'idx':
            continue
        if k == 'sig':
            sig = text
            continue
        if k == 'pre':
            pre = text
            # the statement of reasons: what follows the last 'Exposició de motius' (or 'Preàmbul') heading, after the table of contents
            ls = text.split('\n')
            idx = [i for i, l in enumerate(ls) if re.match(r'^\W*(Exposici[óo] de motius|Pre[àa]mbul)\W*$', l.strip(), re.I)]
            mot = '\n'.join(ls[idx[-1] + 1:]) if idx else ''
            r['w']['motius'] += words(mot)
            r['w']['pre'] += words(text)
        else:
            r['n'][k] += 1
            r['w'][k] += words(text)
            for l in text.split('\n'):
                m = HEAD.match(l)
                if m:
                    r['h'][m.group(1).lower().replace('í', 'i').replace('ó', 'o')] += 1
        body = text
        for key, rx in MENTION:
            c = len(rx.findall(body))
            if c:
                r['m'][key] += c
        for d in DIRNUM.findall(body):
            if d not in r['dirs']:
                r['dirs'].append(d)
        for key, rx in PARISH:
            c = len(rx.findall(body))
            if c:
                r['par'][key] += c
        for m in CONST.finditer(body):
            for num in re.findall(r'(?<![\d.])(\d+)(?:\.\d+)*', m.group(1)):
                if 0 < int(num) <= 107:
                    r['const'][int(num)] += 1
        if k == 'derog':
            r.setdefault('derog_txt', '')
            r['derog_txt'] = (r['derog_txt'] + ' ' + ' '.join(text.split()))[:4000]
        if k in ('final', 'art', 'trans', 'add', 'derog'):
            for key, rx in PRESENT:
                c = len(rx.findall(body))
                if c:
                    r['pres'][key] += c
    sd, span = session_date(pre)
    r['session'] = sd
    r['session_txt'] = span
    r['has_sig'] = bool(sig.strip())
    parsed = signatures(sig)
    if not (parsed['fr'] or parsed['ep'] or parsed['role'] or parsed['pre']):
        # a law with annexed statutes or tables keeps its signatures before them: in the preamble or at the end of its last unit
        for name, text in [('preamble.md', pre)] + [(n_, t_) for n_, t_ in files if kind_of(n_) not in ('pre', 'sig', 'idx')]:
            ls = text.split('\n')
            at = next((i for i, l in enumerate(ls) if re.match(r'^#*\s*Casa de la Vall,', l.strip())), None)
            if at is not None:
                parsed = signatures('\n'.join(ls[at:at + 30]))
                r['sig_in'] = name
                break
    r['sig'] = parsed
    r['motius_head'] = bool(re.search(r'(?m)^\W*(Exposici[óo] de motius|Pre[àa]mbul)\W*$', pre, re.I))
    # a consolidated text approved because no objection was raised within the time limit (Reglament del Consell General, article 116.6)
    r['objection'] = bool(re.search(r'no han estat formulades objeccions|sense objeccions|objeccions', pre[:3000], re.I))
    r['pre_head'] = pre.split('\n', 1)[0][:160]
    for k in ('n', 'w', 'h', 'm', 'par', 'const', 'pres'):
        r[k] = dict(r[k])
    return r


if not a.skip_extract:
    # 1. the history of REF and FUTURE, streamed
    with open(os.path.join(B, 'log.tsv'), 'w', encoding='utf-8', newline='\n') as out:
        out.write('\t'.join(['branch', 'sha', 'author', 'email', 'subject'] + TRAILERS + ['quote']) + '\n')
        n = 0
        for br, r_ in (('main', ref), ('future', f'{ref}..{fut}' if fut else '')):
            if not r_:
                continue
            fmt = '%x1e%H%x1f%an%x1f%ae%x1f%s%x1f%(trailers:unfold,separator=%x1d)%x1f%b'
            lg = subprocess.Popen([*GIT, 'log', r_, '--format=' + fmt], stdout=subprocess.PIPE, env=NOLAZY)
            buf = b''

            def emit(rec):
                global n
                rec = rec.decode('utf-8', 'replace').strip('\n')
                if not rec:
                    return
                p = rec.split('\x1f')
                tr = {}
                for t in (p[4] if len(p) > 4 else '').split('\x1d'):
                    k, _, v = t.partition(': ')
                    if k.strip():
                        tr.setdefault(k.strip(), v.strip())
                q = ''
                for line in (p[5] if len(p) > 5 else '').split('\n'):
                    m = QUOTE.match(line.strip())
                    if m:
                        q = m.group(1)
                        break
                row = [br, p[0], p[1], p[2], p[3]] + [tr.get(k, '') for k in TRAILERS] + [q]
                out.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in row) + '\n')
                n += 1
            for chunk in iter(lambda: lg.stdout.read(1 << 16), b''):
                buf += chunk
                *recs, buf = buf.split(b'\x1e')
                for rec in recs:
                    emit(rec)
            emit(buf)
            lg.wait()
        print('commits', n, flush=True)

    # 2. the tables
    for p in ['laws.csv', 'corpus.json', 'data/stats.json', 'data/amendments.csv', 'data/corrections.csv', 'data/unreadable.csv']:
        oid = git('rev-parse', f'{ref}:{p}').decode().strip()
        fetch_missing([oid])
        data = subprocess.run([*GIT, 'cat-file', 'blob', oid], check=True, capture_output=True, env=NOLAZY).stdout
        open(os.path.join(B, 'repo', p.replace('/', '__')), 'wb').write(data)
    print('tables', flush=True)

    # 3. the trees: every file of every law (the future branch adds the laws in force later)
    laws, seen = {}, set()
    for br, r_ in (('main', ref), ('future', fut)):
        if not r_:
            continue
        for path, oid in tree(r_, 'lleis', 'constitucio'):
            parts = path.split('/')
            folder = '/'.join(parts[:-1])
            if br == 'future' and folder in seen:
                continue
            laws.setdefault(folder, {'br': br, 'files': []})['files'].append((parts[-1], oid))
        if br == 'main':
            seen = set(laws)
    print('laws', len(laws), 'files', sum(len(v['files']) for v in laws.values()), flush=True)
    fetch_missing([o for v in laws.values() for _, o in v['files']])

    # 4. one law at a time: counts only
    with open(os.path.join(B, 'laws.jsonl'), 'w', encoding='utf-8', newline='\n') as out, \
         open(os.path.join(B, 'constitution.jsonl'), 'w', encoding='utf-8', newline='\n') as cout:
        items = [(oid, (folder, name)) for folder in sorted(laws) for name, oid in laws[folder]['files']]
        cur, files = None, []

        def flush_law():
            if cur is None:
                return
            t0 = time.time()
            rec = measure(cur, files)
            if time.time() - t0 > 2:
                print('slow', cur, round(time.time() - t0, 1), 's', flush=True)
            rec['br'] = laws[cur]['br']
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
        for (folder, name), text in read_blobs(items):
            if folder != cur:
                flush_law()
                cur, files = folder, []
            files.append((name, text))
            if folder == 'constitucio' and name != 'index.txt':
                ls = [l for l in text.split('\n') if l.strip()]
                heads = [l.lstrip('#').strip() for l in ls if l.startswith('## ')]
                body = [l for l in ls if not l.startswith('#')]
                cout.write(json.dumps({'file': name, 'heads': heads, 'words': words(text),
                                       'head': next((l.lstrip('#').strip() for l in ls if l.startswith('# ')), ''),
                                       'first': (body[0][:160] if body else ''),
                                       'lq': bool(re.search(r'\bLlei Qualificada\b|\blleis qualificades\b', text, re.I))}, ensure_ascii=False) + '\n')
        flush_law()
    print('measured', len(laws), flush=True)
    del laws

# 5. numbers, then the page
if a.extract_only:
    sys.exit(0)
subprocess.run([sys.executable, '-X', 'utf8', os.path.join(HERE, 'prep.py'), '--ref-sha', sha, '--future-sha', fsha], check=True)
subprocess.run([sys.executable, '-X', 'utf8', os.path.join(HERE, 'build.py'), os.path.join(B, 'data.json'), a.out], check=True)
