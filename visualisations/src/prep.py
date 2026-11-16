"""Compute every number of the 20 charts from visualisations/src/.build/ (written by make.py) into .build/data.json.

The rules that classify a law (its kind, whether it is a qualified law, its subject, the tax or code it belongs to)
read the law's title as the BOPA published it; whatever no rule recognises is counted as "other". The law a later law
says it changes is the folder data/amendments.csv gives, or else the law whose name and date (or number) the
sentence cites (resolve() below); names it cannot match are left out and counted.
"""
import argparse, csv, json, os, re, statistics, unicodedata, datetime as dt
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, '.build')
ap = argparse.ArgumentParser()
ap.add_argument('--ref-sha', default='')
ap.add_argument('--future-sha', default='')
a = ap.parse_args()

D = dt.date.fromisoformat
MES = ['gener', 'febrer', 'març', 'abril', 'maig', 'juny', 'juliol', 'agost', 'setembre', 'octubre', 'novembre', 'desembre']
meta = list(csv.DictReader(open(os.path.join(B, 'repo', 'laws.csv'), encoding='utf-8')))
AM = list(csv.DictReader(open(os.path.join(B, 'repo', 'data__amendments.csv'), encoding='utf-8')))
CORR = list(csv.DictReader(open(os.path.join(B, 'repo', 'data__corrections.csv'), encoding='utf-8')))
STATS = json.load(open(os.path.join(B, 'repo', 'data__stats.json'), encoding='utf-8'))
CORPUS = json.load(open(os.path.join(B, 'repo', 'corpus.json'), encoding='utf-8'))
LOG = list(csv.DictReader(open(os.path.join(B, 'log.tsv'), encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
TX = {}
for l in open(os.path.join(B, 'laws.jsonl'), encoding='utf-8'):
    r = json.loads(l)
    TX[r['f']] = r
CONST = [json.loads(l) for l in open(os.path.join(B, 'constitution.jsonl'), encoding='utf-8')]
RECORD_TO = CORPUS.get('record_to', STATS.get('last'))
BUILT = CORPUS.get('built', STATS.get('today'))
LAST_PUB = STATS.get('last_published')


# ------------------------------------------------------------------ titles, dates and names
def clean(t):
    t = t.replace('​', '').replace('\xa0', ' ').replace('’', "'").strip()
    t = re.sub(r'^L\s+lei\b', 'Llei', t)
    t = re.sub(r'^(?:Llei\s+)+(?=Llei\b)', '', t)
    return re.sub(r'\s+', ' ', t)


def y2(y):
    y = int(y)
    return (1900 + y if y > 50 else 2000 + y) if y < 100 else y


def safe_date(y, m, d):
    try:
        return dt.date(int(y), int(m), int(d))
    except ValueError:
        return None


def title_date(t):
    """the date of the law's own citation: 'Llei 31/2018, del 6 de desembre' / '..., de 3-9-93' / 'Decret de 27-2-92 ...'"""
    m = re.match(r"^(?:Llei|Edicte|Decret)\s+de\s+(\d{1,2})-(\d{1,2})-(\d{2,4})\b", t)
    if m:
        return safe_date(y2(m.group(3)), m.group(2), m.group(1))
    m = re.match(r"^[Ll]lei\s+(?:qualificada\s+)?(\d{1,3})\s*[/-]\s*(\d{2,4}),?\s+(?:del?\s+|de l')\s*(\d{1,2})\s+(?:de\s+|d')(\w+)", t)
    if m and m.group(4).lower() in MES:
        return safe_date(y2(m.group(2)), MES.index(m.group(4).lower()) + 1, m.group(3))
    m = re.match(r"^[Ll]lei\s+(\d{1,3})/(\d{4})\s+del\s+(\d{1,2})-(\d{1,2})-(\d{4})", t)
    if m:
        return safe_date(m.group(5), m.group(4), m.group(3))
    m = re.search(r"(?:\bde[l]?\s*|\bd'\s*|,\s*)(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{2,4})\.?\s*$", t)
    if m:
        return safe_date(y2(m.group(3)), m.group(2), m.group(1))
    m = re.search(r"\bde\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})\s*$", t)
    if m and m.group(2).lower() in MES:
        return safe_date(m.group(3), MES.index(m.group(2).lower()) + 1, m.group(1))
    return None


def dates_in(t):
    out = []
    for m in re.finditer(r'(\d{1,2})\s*-\s*(\d{1,2})\s*-\s*(\d{2,4})', t):
        d = safe_date(y2(m.group(3)), m.group(2), m.group(1))
        if d:
            out.append((m.start(), d))
    for m in re.finditer(r"(\d{1,2})\s+(?:de\s+|d')(" + '|'.join(MES) + r")\s+(?:de[l]?\s+)?(\d{4})", t, re.I):
        d = safe_date(m.group(3), MES.index(m.group(2).lower()) + 1, m.group(1))
        if d:
            out.append((m.start(), d))
    return [d for _, d in sorted(out)]


def strip_acc(s):
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


STOP = re.compile(r"^(?:de la |del |de l'|de les |dels |d'|de |sobre |relativa a |relatiu a |reguladora de(?:l| la| les| l')? |general de(?:l| la| l')? )+")


def core(name):
    """a law's name without citation, date and leading words: 'Llei qualificada de la Justícia, de 3-9-93' -> 'justicia'"""
    s = clean(name)
    s = re.sub(r"^Decret pel qual es publica (?:el |la )?", '', s, flags=re.I)
    s = re.sub(r"^Llei\s+de\s+\d{1,2}-\d{1,2}-\d{2,4}\s+", 'Llei ', s, flags=re.I)
    s = re.sub(r"^Llei\s+(?:qualificada\s+)?\d{1,3}\s*[/-]\s*\d{2,4},?\s+(?:del?\s+|de l')\d{1,2}\s+(?:de\s+|d')\w+(?:\s+de[l]?\s+\d{4})?,?\s*", 'Llei ', s, flags=re.I)
    s = re.sub(r"^Llei\s+(?:qualificada\s+)?\d{1,3}\s*[/-]\s*\d{2,4},?\s*", 'Llei ', s, flags=re.I)
    s = re.sub(r",?\s*(?:de[l]?|d')\s*(?:data\s+)?\d{1,2}(?:\s*-\s*\d{1,2}\s*-\s*\d{2,4}|\s+(?:de\s+|d')\w+\s+(?:de[l]?\s+)?\d{4})\.?\s*$", '', s)
    s = re.sub(r",\s*\d{1,2}-\d{1,2}-\d{2,4}\s*$", '', s)
    s = strip_acc(s.lower())
    s = re.sub(r"^llei\s+", '', s)
    s = re.sub(r"^(?:qualificada\s+)?(?:de\s+text\s+consolidat\s+)?(?:qualificada\s+)?", '', s)
    s = re.sub(r"[^a-z0-9' ]+", ' ', s)
    s = re.sub(r"\s+", ' ', s).strip()
    return STOP.sub('', s)


# ------------------------------------------------------------------ the laws
LOGBY = {}
for r in LOG:
    if r.get('Kind') == 'enacted' and r.get('Source'):
        LOGBY[r['Source'].strip()] = r

DOC = re.compile(r"^(?:Edicte\b|Pressupost per al \d{4}|Exercici \d{4}|Taula de la Llei|Quadres? resum|Decret de \d{1,2}-\d{1,2}-\d{2} pel qual se subsana)", re.I)
CREDIT = re.compile(r"\bcr[èe]dits? (?:extraordinaris?|pressupostaris?)\b|\bsuplements? de cr[èe]dit|\bavenç(?:os)? de fons|\bcr[èe]dit extraordin[àa]ri", re.I)
BUDGET = re.compile(r"\bpressupost(?: general)? (?:per a|per al|per l'|de l'exercici)|\bpressupost extraordinari\b", re.I)
AMEND = re.compile(r"\bmodificaci[óo]\b|\bacompanyament\b|\breforma del\b|\baddici[óo] de l'article\b|\bmodifica\b", re.I)
QUAL = re.compile(r"^[Ll]lei\s+qualificada\b|^[Ll]lei\s+(?:qualificada\s+)?\d{1,3}\s*[/-]\s*\d{2,4},?\s+(?:del?\s+|de l')\s*\d{1,2}\s+(?:de\s+|d')\w+,?\s+(?:de text consolidat\s+)?qualificad[ao]\b")
ANNUAL = re.compile(r"\bpressupost(?: general)?\s+per\s+a(?:l)?\s+(?:l'exercici\s+)?(?:de(?:l)?\s+)?(\d{4})\b", re.I)

LAWS = {}
for m in meta:
    f = m['folder']
    t = clean(m['title'])
    x = TX.get(f, {})
    lg = LOGBY.get(m['source'].strip(), {})
    kind = ('const' if f == 'constitucio' else 'doc' if DOC.search(t) else 'credit' if CREDIT.search(t) else
            'consol' if re.search(r"\btext consolidat\b", t, re.I) else
            'budget' if BUDGET.search(t) and not AMEND.search(t) else 'amend' if AMEND.search(t) else 'new')
    sig = x.get('sig', {})
    ad = title_date(t) or (D(sig['date']) if sig.get('date') else None) or (D(x['session']) if x.get('session') else None)
    w = x.get('w', {})
    n = x.get('n', {})
    LAWS[f] = dict(
        f=f, t=t, pub=m['published'], inf=m['in_force'], basis=m['in_force_basis'], br=m['branch'], units=int(m['units'] or 0),
        y=int(m['published'][:4]), kind=kind, q=bool(QUAL.search(t)), ad=ad.isoformat() if ad else None,
        adsrc='title' if title_date(t) else 'sig' if sig.get('date') else 'session' if x.get('session') else None,
        sigdate=sig.get('date'), session=x.get('session'),
        extra='extra' in (lg.get('Bulletin') or ''), quote=lg.get('quote', ''),
        words=sum(w.get(k, 0) for k in ('art', 'add', 'trans', 'derog', 'final', 'annex', 'other')),
        motius=w.get('motius', 0), n=n, w=w, h=x.get('h', {}),
        fr=sig.get('fr'), ep=sig.get('ep'), sindic=sig.get('sindic'), role=sig.get('role'), pre=sig.get('pre'), place=sig.get('place'),
        m=x.get('m', {}), dirs=x.get('dirs', []), const=x.get('const', {}), pres=x.get('pres', {}), par=x.get('par', {}),
        objection=x.get('objection', False),
        core=core(t))
L = LAWS
ACTS = [l for l in L.values() if l['kind'] != 'const']                  # the 1,040 texts the README calls laws
LAWLIKE = [l for l in ACTS if l['kind'] != 'doc']                       # without the edicts and budget tables
print('laws', len(ACTS), 'without documents', len(LAWLIKE), Counter(l['kind'] for l in ACTS))
print('qualified', sum(1 for l in LAWLIKE if l['q']))
SIND_FIX = {'Josep Dalleres Codina': 'Josep Dallerès Codina', 'Jordi Farrás Forné': 'Jordi Farràs Forné', 'Jordi Farràs Fornés': 'Jordi Farràs Forné'}
for l in L.values():
    if l['sindic']:
        l['sindic'] = SIND_FIX.get(l['sindic'], l['sindic'])

# ------------------------------------------------------------------ the Síndic General's terms, from the signatures
CONST_DAY = L['constitucio']['inf']                                     # 1993-05-03
runs = []
for name in sorted({l['sindic'] for l in L.values() if l['sindic'] and l['role'] and l['role'].startswith('Síndic')}):
    ds = sorted(l['ad'] for l in L.values() if l['sindic'] == name and l['role'].startswith('Síndic') and l['ad'])
    cur = [ds[0], ds[0]]
    for d in ds[1:]:
        if (D(d) - D(cur[1])).days > 400:
            runs.append([name, cur[0], cur[1]])
            cur = [d, d]
        else:
            cur[1] = d
    runs.append([name, cur[0], cur[1]])
runs.sort(key=lambda r: r[1])
TERMS = [{'id': 'pre', 'name': None, 'from': '1989-01-01', 'to': CONST_DAY}]
for i, (name, d0, d1) in enumerate(runs):
    start = max(d0, CONST_DAY) if i == 0 else d0
    TERMS.append({'id': f't{i + 1}', 'name': name, 'from': start, 'first': d0, 'last': d1,
                  'female': any(l['role'] == 'Síndica General' for l in L.values() if l['sindic'] == name)})
for i, t in enumerate(TERMS):
    t['to'] = TERMS[i + 1]['from'] if i + 1 < len(TERMS) else RECORD_TO
print('terms', [(t['name'], t['from'], t['to']) for t in TERMS])


def term_of(d):
    for t in TERMS:
        if t['from'] <= d < t['to'] or (t is TERMS[-1] and d >= t['from']):
            return t['id']
    return 'pre'


for l in L.values():
    l['term'] = term_of(l['ad'] or l['pub'])

# ------------------------------------------------------------------ amendments: the law each sentence names
BYCORE = defaultdict(list)
for l in L.values():
    BYCORE[l['core']].append(l)
# a later text of the same code: the 1998 Code of Criminal Procedure (273 articles) is titled as a modification
ALIAS = {'lleis/1999-01-06-17caa': 'codi de procediment penal'}
for f, c in ALIAS.items():
    if f in L:
        BYCORE[c].append(L[f])
for ls in BYCORE.values():
    ls.sort(key=lambda l: l['pub'])
BYNUM = {}
for l in L.values():
    mm = re.match(r"^[Ll]lei\s+(?:qualificada\s+)?(\d{1,3})\s*[/-]\s*(\d{2,4})\b", l['t'])
    if mm:
        BYNUM.setdefault((int(mm.group(1)), y2(mm.group(2))), l['f'])
NUMRX = re.compile(r"\bLlei\s+(?:qualificada\s+)?(\d{1,3})\s*/\s*(\d{4})\b")


def law_dates(l):
    ds = dates_in(l['t'])
    if l['ad']:
        ds.append(D(l['ad']))
    return ds


def resolve(name, before):
    nme = clean(name)
    mm = NUMRX.search(nme)
    if mm and (int(mm.group(1)), int(mm.group(2))) in BYNUM:
        return BYNUM[(int(mm.group(1)), int(mm.group(2)))]
    c = core(nme)
    ds = dates_in(nme)
    cands = [l for l in BYCORE.get(c, []) if l['pub'] < before]
    if not cands and len(c) >= 6:   # a name that begins a longer title, or the other way round
        cands = sorted([l for k, ls in BYCORE.items() if len(k) >= 6 and (k.startswith(c) or c.startswith(k)) for l in ls if l['pub'] < before],
                       key=lambda l: l['pub'])
    if ds:
        hit = [l for l in cands if any(abs((d - ds[-1]).days) <= 31 for d in law_dates(l))]
        return hit[-1]['f'] if hit else None
    return cands[-1]['f'] if cands else None


CH = []          # one row per stated change: (amending folder, target folder or None, kind, file kind)
unresolved = Counter()
for r in AM:
    src = '/'.join(r['file'].split('/')[:2])
    if src not in L:
        continue
    tgt = r['amended_folder'] or resolve(r['amended_law'], L[src]['pub'])
    # no law changes the Constitution (article 106); the one sentence naming «Constitució» rewrites an article so headed
    if tgt == src or tgt == 'constitucio':
        tgt = None
    fname = r['file'].split('/')[-1]
    fk = ('final' if fname.startswith('disposicio-final') else 'add' if fname.startswith('disposicio-addicional') else
          'trans' if fname.startswith('disposicio-transitoria') else 'derog' if fname.startswith('disposicio-derogatoria') else 'art')
    CH.append((src, tgt, r['kind'], fk, r['provision'] == '(whole)'))
    if not tgt:
        unresolved[r['amended_law'][:60]] += 1
print('changes', len(CH), 'resolved', sum(1 for c in CH if c[1]), 'unresolved', sum(unresolved.values()))


def yrs(a0, a1):
    return list(range(a0, a1 + 1))


YEARS = yrs(1989, int(RECORD_TO[:4]))
out = {}

# ------------------------------------------------------------------ 1. the laws by year and kind
KINDS = ['new', 'amend', 'consol', 'budget', 'credit', 'doc']
c01 = {'years': {}, 'terms': [], 'future': [], 'const': {'pub': L['constitucio']['pub'], 'ad': L['constitucio']['ad']}}
for y in YEARS:
    c01['years'][y] = {k: sum(1 for l in ACTS if l['y'] == y and l['kind'] == k) for k in KINDS}
for t in TERMS:
    ls = [l for l in LAWLIKE if l['term'] == t['id']]
    c01['terms'].append({'id': t['id'], 'name': t['name'], 'from': t['from'], 'to': t['to'], 'female': t.get('female', False), 'n': len(ls),
                         'q': sum(1 for l in ls if l['q']), 'kinds': {k: sum(1 for l in ls if l['kind'] == k) for k in KINDS}})
c01['future'] = [[l['f'], l['t'], l['pub'], l['inf']] for l in ACTS if l['br'] == 'future']
c01['n'] = len(ACTS)
c01['lawlike'] = len(LAWLIKE)
c01['docs'] = [[l['f'], l['t'], l['pub']] for l in ACTS if l['kind'] == 'doc']
c01['by_kind'] = dict(Counter(l['kind'] for l in ACTS))
out['c01'] = c01

# ------------------------------------------------------------------ 2. subjects
SUBJ = [
    ('budget', r"\bcr[èe]dits? (?:extraordinari|pressupostari)|\bsuplements? de cr[èe]dit|\bpressupost|\bavenç(?:os)? de fons|\bpla d'equilibri financer|\bmarc pressupostari"),
    ('tax', r"\bimpost|\btax(?:a|es)\b|\btribut|\btarifa general|\bc[àa]non\b|\bfiscal|\bIMI\b|\bduan|\bmòduls aplicables"),
    ('fin', r"\bentitats? (?:banc|financ|operatives|d'inversi|gestores)|\bsistema financer|\bbanc(?:a|ari|àri|àries)\b|\bfinancer|\bassegura|\bblanqueig|\bvalors\b|\binversi[óo] col·lectiva|\bsolvència|\bInstitut Nacional Andorrà de Finances|\bAutoritat Financera|\bcoeficient d'inversions|\breserves en garantia|\bserveis de pagament|\bdiner electrònic|\bcriptogr|\bactius digitals|\bcadena de blocs|\bauditoria|\bcomptabilitat|\bconglomerats|\bmercats? de valors|\bsecret bancari|\bdipòsits|\btransici[óo] cap a l'euro|\bmorositat|\bembargament|\bgarantia de dipòsits|\bAutoritat Monetària|\bFons de Reserva de Jubilaci"),
    ('just', r"\bpenal|\bJust[íi]cia\b|\bTribunal|\bjudicial|\bprocediment civil|\bprocediments judicials|\bpenitenci|\bMinisteri Fiscal|\bnotari|\badvocat|\bsaig\b|\bextradici|\bjurisdicci|\barbitratge|\bprocuradors|\bmediaci|\bassistència lletrada|\bBatllia|\bbatlles|\btràfic d'éssers humans|\btraducció i/o la interpretació jurades|\bperits"),
    ('inst', r"\bConsell General\b|\belectoral|\brefer[èe]ndum|\bnacionalitat|\bpartits pol|\bRaonador|\bdades personals|\bassociacions|\bfundacions|\bentitats religioses|\bConstituci|\bprotocol|\bestats d'alarma|\bdrets de la persona|\bintimitat|\btransparència|\bGovern\b|\bsignes d'estat|\bTractats|\bcens\b|\bNúmero d'Identificació|\bSíndics|\bButlletí Oficial|\bvoluntariat|\bCreu Roja|\bFòrum Nacional de la Joventut|\bllibertat sindical|\bacció sindical|\bconflicte col"),
    ('fam', r"\bmatrimoni|\bunions?\b|\bparella|\bfam[íi]lia|\badopci|\bmenors?\b|\binfants|\bincapacitaci|\breproducci[óo] humana|\bRegistre Civil|\bsuccessori|\bsuccessió|\bviolència de gènere|\bigualtat|\bguarderies"),
    ('work', r"\blaborals?\b|\bseguretat social|\bCaixa Andorrana de Seguretat Social|\btreball|\bocupaci[óo]\b|\bpensi[óo]|\bjubilaci|\bfunci[óo] pública|\bsalari|\bvellesa|\bReglament (?:d'Aplicació|Tècnic)"),
    ('health', r"\bsanit|\bsalut|\bmedicament|\bfarmàc|\bdiscapacitat|\bserveis socials|\bgent gran|\bdependència|\bdrogues|\btabac|\balcohol|\bhospital|\bAntidopatge|\bbiomèdica|\bòrgans, cèl·lules|\bCol·legi Oficial de (?:Farmac|Logop|Psicòl|Fisiot|Infermer|Dietist|Podòl|Tècnics Ortop)|\bCol\.legi Oficial de Podòl|\baccessibilitat"),
    ('edu', r"\beducaci|\bEscola\b|\buniversit|\bensenyament|\bformaci[óo] professional|\bpatrimoni cultural|\bllengua|\besport|\bbeques|\bestudi|\bcultura|\bbiblioteques|\bmuseus|\barxius|\bqualificacions|\baprenentatge|\bRàdio|\bradiodifusi|\btelevisi|\bsistema educatiu|\brecerca|\bJoventut"),
    ('terr', r"\burban|\bterritori|\bcarreter|\bhabitatge|\bmedi ambient|\baig[üu]|\benergi|\belèctric|\bresidus|\bcaça|\bpesca|\bagricultura|\bramader|\bbosc|\bestacions de muntanya|\bimmobil|\barrendaments|\bpropietat horitzontal|\bexpropiaci|\bcanvi climàtic|\bnatural|\bvedats|\bcirculació|\btransport|\bcomunicacions|\btelecomunicacions|\bconstrucci|\bcartografia|\bcadastre|\banimals|\bvehicle|\bnavegació aèria|\bgasos combustibles|\bFEDA\b|\bForces Elèctriques|\bmatrícula|\beconomia circular|\bavaluació ambiental|\bradioafició|\bradioelèctriques|\bAndorra Telecom|\bSTA\b|\bTelecomunicacions"),
    ('econ', r"\bsocietats\b|\bcomerç|\bempres|\binversi(?:[óo]|ons) estrangera|\bturís|\bmarques|\bpatents|\bconsum(?:idors)?\b|\bcompetència|\bdigital|\bpropietat intel|\bdrets d'autor|\bcambra|\bjocs? d'atzar|\bbingo|\bcasinos|\bmercaderies|\bindústria|\bindustrial|\bcomercial|\bemprenedoria|\bestadística|\bRecull Estadístic|\bactivitat econòmica|\breactivació econòmica|\bprofessionals liberals|\bCol·legi Oficial d'(?:Economistes|Enginyers)|\bCol·legi Oficial de Geòlegs|\bsignatura electrònica|\bconfiança electrònica|\ballotjament|\bDesenvolupament i Inversió|\bassegurances d'automòbil|\bAssegurança d'Automòbil|\bGarantia d'Automòbils|\bcooperatives"),
    ('adm', r"\bAdministraci[óo]|\bcontractaci[óo] pública|\bfinances (?:públiques|comunals)|\bTribunal de Comptes|\bComuns?\b|\bcomuns?\b|\bParròquia|\bpatrimoni de l'Estat|\bpolicia|\bPolicia|\bseguretat pública|\bprotecció civil|\bbombers|\bBanders|\bIncendis|\bCentre Nacional d'Informàtica|\bInstitut d'Estudis Andorrans|\bpersonal|\bsocietat pública|\bens públic"),
    ('immig', r"\bimmigraci|\bresid[èe]nci|\bestrangers|\bpassaport"),
]
SUBJ_RX = [(k, re.compile(rx, re.I)) for k, rx in SUBJ]
SUBJ_KEYS = [k for k, _ in SUBJ] + ['other']


def subject(l):
    if l['kind'] in ('credit', 'budget'):
        return 'budget'
    t = l['t']
    # 'Llei de modificació de la Llei X': the subject is X's
    for k, rx in SUBJ_RX:
        if rx.search(t):
            return k
    return 'other'


for l in L.values():
    l['subj'] = subject(l) if l['kind'] not in ('const', 'doc') else None
PER5 = [(1989, 1993), (1994, 1998), (1999, 2003), (2004, 2008), (2009, 2013), (2014, 2018), (2019, 2023), (2024, int(RECORD_TO[:4]))]
c02 = {'periods': [[p0, p1] for p0, p1 in PER5], 'subjects': SUBJ_KEYS, 'cells': {}, 'tot': {}, 'other': [], 'n': len(LAWLIKE)}
for k in SUBJ_KEYS:
    c02['cells'][k] = [sum(1 for l in LAWLIKE if l['subj'] == k and p0 <= l['y'] <= p1) for p0, p1 in PER5]
    c02['tot'][k] = sum(c02['cells'][k])
c02['ptot'] = [sum(1 for l in LAWLIKE if p0 <= l['y'] <= p1) for p0, p1 in PER5]
c02['other'] = [[l['f'], l['t'], l['y']] for l in LAWLIKE if l['subj'] == 'other']
c02['examples'] = {k: [[l['t'], l['y']] for l in sorted((l for l in LAWLIKE if l['subj'] == k), key=lambda l: -l['words'])[:3]] for k in SUBJ_KEYS}
out['c02'] = c02
print('subjects', c02['tot'])

# ------------------------------------------------------------------ 3. the Constitution
TIT = None
arts = []
for c in CONST:
    for h in c['heads']:
        if re.match(r'^T[íi]tol\b', h):
            TIT = {'name': h, 'sub': None}
        elif TIT is not None and TIT['sub'] is None and not re.match(r'^Cap[íi]tol\b', h):
            TIT['sub'] = h
    f = c['file']
    num = int(re.search(r'article-(\d+)', f).group(1)) if f.startswith('article-') else None
    kind = 'art' if num else 'pre' if f == 'preamble.md' else 'sig' if f == 'signatures.md' else 'disp'
    arts.append({'file': f, 'num': num, 'kind': kind, 'tit': (TIT['name'] if TIT and kind == 'art' else None), 'tsub': (TIT['sub'] if TIT and kind == 'art' else None),
                 'words': c['words'], 'first': c['first'], 'lq': c['lq'], 'head': c['head']})
cite = defaultdict(list)
for l in LAWLIKE:
    for k, v in l['const'].items():
        cite[int(k)].append([l['f'], l['t'], l['y']])
for x in arts:
    x['cited'] = sorted(cite.get(x['num'], []), key=lambda r: r[2]) if x['num'] else []
c03 = {'arts': arts, 'laws_citing': sum(1 for l in LAWLIKE if l['const']), 'n': len(LAWLIKE),
       'cites': sum(sum(l['const'].values()) for l in LAWLIKE), 'words': sum(x['words'] for x in arts if x['kind'] in ('art', 'disp', 'pre')),
       'pub': L['constitucio']['pub'], 'ad': L['constitucio']['ad']}
out['c03'] = c03

# ------------------------------------------------------------------ 4. qualified laws
QM = [
    ('penal', r"\bpenal|\bpenitenci|\bmenors? d'edat\b|\bjurisdicció de menors|\bextradici"),
    ('just', r"\bJust[íi]cia\b|\bTribunal Constitucional|\bcontrol previ de constitucionalitat|\bTractats\b"),
    ('elect', r"\belectoral|\brefer[èe]ndum|\bpartits pol"),
    ('comuns', r"\bcomuns\b"),
    ('nat', r"\bnacionalitat|\bimmigraci|\bresidències passives"),
    ('fam', r"\bmatrimoni|\bunions?\b|\bparella|\bfam[íi]lia|\badopci|\binfants|\bincapacitaci|\breproducci[óo] humana"),
    ('rights', r"\bassociacions|\bdades personals|\bllibertat sindical|\bacció sindical|\bconflicte col|\bintimitat|\bentitats religioses|\beducaci"),
    ('sec', r"\bPolicia|\bseguretat pública|\bestats d'alarma|\bprotecció civil"),
    ('pension', r"\bpla de pensions"),
    ('other', r"."),
]
QM_RX = [(k, re.compile(rx, re.I)) for k, rx in QM]


def qmatter(t):
    # the law's own subject: what follows 'qualificada de/del ...' (a law amending a qualified law takes that law's matter)
    for k, rx in QM_RX:
        if rx.search(t):
            return k
    return 'other'


QL = sorted((l for l in LAWLIKE if l['q']), key=lambda l: l['pub'])
for l in QL:
    l['qm'] = qmatter(l['t'])
c04 = {'matters': [k for k, _ in QM], 'laws': [[l['f'], l['t'], l['ad'] or l['pub'], l['qm'], l['kind'], l['term'], l['words']] for l in QL],
       'terms': [{'id': t['id'], 'n': sum(1 for l in LAWLIKE if l['term'] == t['id']), 'q': sum(1 for l in QL if l['term'] == t['id'])} for t in TERMS],
       'n': len(QL), 'all': len(LAWLIKE),
       'by_amending': sum(1 for l in LAWLIKE if not l['q'] and re.search(r"\bLlei qualificada\b", l['t'], re.I) and l['kind'] == 'amend'),
       'reserve': [x['num'] for x in arts if x['lq'] and x['num']]}
out['c04'] = c04
print('qualified by matter', Counter(l['qm'] for l in QL))

# ------------------------------------------------------------------ 5. the codes (laws whose title names a code), with the person and family law
CODES = [
    ('penal', r"\bCodi Penal\b(?!.*\bmodificaci)", ['lleis/1990-07-29-13922', 'lleis/2005-009', 'lleis/2026-018']),
    ('ppenal', r"", ['lleis/1989-02-26-143be', 'lleis/1999-01-06-17caa']),
    ('admin', r"", ['lleis/1989-04-09-14772', 'lleis/2023-07-26-cgl_2023_07_20_10_17_14']),
    ('duana', r"", ['lleis/1996-07-09-b61a', 'lleis/2004-005', 'lleis/2020-017', 'lleis/2025-010']),
    ('circ', r"", ['lleis/1999-07-13-199a6', 'lleis/2021-012']),
    ('lab', r"", ['lleis/2008-035', 'lleis/2018-031']),
    ('pcivil', r"", ['lleis/2018-024', 'lleis/2021-022']),
]
# check the lists against the titles: every law whose title names a code (and is not a modification, a decree of
# errata or a credit law) must be in one of them
named = [l['f'] for l in LAWLIKE if re.search(r"\bCodi\b", l['t']) and l['kind'] in ('new', 'consol') and not CREDIT.search(l['t'])]
listed = {f for _, _, fs in CODES for f in fs}
extra = [f for f in named if f not in listed]
print('codes named but not listed:', extra)
def names_law(txt, l):
    """does this text (a derogatory disposition) name law l: by its number, or by its date written out?"""
    mm = re.match(r"^[Ll]lei\s+(?:qualificada\s+)?(\d{1,3})\s*[/-]\s*(\d{2,4})\b", l['t'])
    if mm and re.search(r"\bLlei\s+(?:qualificada\s+)?" + mm.group(1) + r"\s*/\s*" + str(y2(mm.group(2))) + r"\b", txt, re.I):
        return True
    d = D(l['ad']) if l['ad'] else None
    if d:
        for x in dates_in(txt):
            if x == d:
                return True
    return False


c05 = {'codes': [], 'family': None, 'civil_code': [l['f'] for l in ACTS if re.search(r"\bCodi civil\b", l['t'], re.I)]}
for key, _, fs in CODES:
    eds = []
    for i, f in enumerate(fs):
        l = L[f]
        nxt = L[fs[i + 1]] if i + 1 < len(fs) else None
        eds.append({'f': f, 't': l['t'], 'ad': l['ad'], 'pub': l['pub'], 'inf': l['inf'], 'br': l['br'], 'words': l['words'], 'art': l['n'].get('art', 0),
                    'kind': l['kind'], 'q': l['q'], 'changes': sum(1 for c in CH if c[1] == f), 'by': len({c[0] for c in CH if c[1] == f}),
                    'repealed_by_next': bool(nxt and names_law(TX.get(nxt['f'], {}).get('derog_txt', ''), l))})
    c05['codes'].append({'key': key, 'eds': eds})
fam = L['lleis/2022-030']
c05['family'] = {'f': fam['f'], 't': fam['t'], 'ad': fam['ad'], 'inf': fam['inf'], 'words': fam['words'], 'art': fam['n'].get('art', 0),
                 'repeals': sorted({c[1] for c in CH if c[0] == fam['f'] and c[2] == 'repeal' and c[4] and c[1]})}
out['c05'] = c05

# ------------------------------------------------------------------ 6. length of new laws
c06 = {'years': {}, 'longest': [], 'periods': []}
NEW = [l for l in LAWLIKE if l['kind'] == 'new']
for y in YEARS:
    ws = [l['words'] for l in NEW if l['y'] == y]
    c06['years'][y] = {'n': len(ws), 'med': statistics.median(ws) if ws else None, 'max': max(ws) if ws else None}
PER = [(1989, 1992), (1993, 1999), (2000, 2009), (2010, 2019), (2020, int(RECORD_TO[:4]))]
for p0, p1 in PER:
    ws = [l['words'] for l in NEW if p0 <= l['y'] <= p1]
    ms = [l['motius'] for l in NEW if p0 <= l['y'] <= p1]
    c06['periods'].append({'p': [p0, p1], 'n': len(ws), 'med': statistics.median(ws), 'motius': statistics.median(ms)})
c06['longest'] = [[l['f'], l['t'], l['ad'] or l['pub'], l['words'], l['n'].get('art', 0), l['kind'], l['br']] for l in sorted(LAWLIKE, key=lambda l: -l['words'])[:14]]
c06['total_words'] = sum(l['words'] for l in LAWLIKE)
c06['n_new'] = len(NEW)
out['c06'] = c06

# ------------------------------------------------------------------ 7. the co-princes' signatures
FRN = ['mitterrand', 'chirac', 'sarkozy', 'hollande', 'macron']
EPN = ['marti', 'vives', 'serrano']
POST = [l for l in L.values() if l['kind'] not in ('doc',) and l['f'] != 'constitucio' and l['ad'] and l['ad'] >= CONST_DAY]
for l in POST:
    l['cp'] = 'both' if l['fr'] and l['ep'] else 'fr' if l['fr'] else 'ep' if l['ep'] else 'none'
c07 = {'laws': [[l['f'], l['ad'], l['cp'], l['fr'], l['ep'], l['t'], l['q']] for l in sorted(POST, key=lambda l: l['ad'])],
       'princes': {}, 'none': [[l['f'], l['t'], l['ad']] for l in POST if l['cp'] == 'none'],
       'pre': Counter(('delegats' if l['pre'] == 'delegats' else 'veguers' if l['pre'] == 'veguers' else 'sindic' if l['role'] else 'none')
                      for l in L.values() if l['kind'] not in ('doc',) and l['f'] != 'constitucio' and (not l['ad'] or l['ad'] < CONST_DAY)),
       'const_sig': {'fr': L['constitucio']['fr'], 'ep': L['constitucio']['ep']}}
for p in FRN + EPN:
    side = 'fr' if p in FRN else 'ep'
    ls = [l for l in POST if l[side] == p]
    if not ls:
        continue
    ds = sorted(l['ad'] for l in ls)
    c07['princes'][p] = {'side': side, 'n': len(ls), 'first': ds[0], 'last': ds[-1], 'alone': sum(1 for l in ls if l['cp'] == side),
                         'q': sum(1 for l in ls if l['q'])}
out['c07'] = c07
print('co-princes', {k: (v['n'], v['alone']) for k, v in c07['princes'].items()}, Counter(l['cp'] for l in POST))

# ------------------------------------------------------------------ 8. the calendar of approvals
SESS = [l for l in LAWLIKE if l['ad'] and l['kind'] != 'consol']
c08 = {'cells': {}, 'dow': [0] * 7, 'dow_consol': [0] * 7, 'n': len(SESS), 'month': [0] * 12, 'days': {}}
for l in SESS:
    d = D(l['ad'])
    c08['cells'].setdefault(d.year, [0] * 12)[d.month - 1] += 1
    c08['dow'][d.weekday()] += 1
    c08['month'][d.month - 1] += 1
for l in LAWLIKE:
    if l['ad'] and l['kind'] == 'consol':
        c08['dow_consol'][D(l['ad']).weekday()] += 1
byday = Counter(l['ad'] for l in SESS)
c08['busiest'] = [[d, n, [L_['t'] for L_ in SESS if L_['ad'] == d][:3]] for d, n in byday.most_common(6)]
c08['session_days'] = len(byday)
out['c08'] = c08

# ------------------------------------------------------------------ 9. from approval to the BOPA
LAGB = [(0, 15), (16, 21), (22, 28), (29, 35), (36, 10 ** 6)]
c09 = {'terms': [], 'bins': LAGB, 'neg': [], 'all': []}
for t in TERMS:
    ls = [l for l in LAWLIKE if l['ad'] and l['term'] == t['id']]
    lags = []
    for l in ls:
        g = (D(l['pub']) - D(l['ad'])).days
        if g < 0:
            c09['neg'].append([l['f'], l['t'], l['ad'], l['pub']])
            continue
        lags.append(g)
    c09['terms'].append({'id': t['id'], 'n': len(lags), 'bins': [sum(1 for g in lags if b0 <= g <= b1) for b0, b1 in LAGB],
                         'med': statistics.median(lags) if lags else None})
    c09['all'] += lags
c09['med'] = statistics.median(c09['all'])
c09['long'] = [[l['f'], l['t'], l['ad'], l['pub'], (D(l['pub']) - D(l['ad'])).days] for l in
               sorted((l for l in LAWLIKE if l['ad'] and (D(l['pub']) - D(l['ad'])).days > 90), key=lambda l: -(D(l['pub']) - D(l['ad'])).days)]
c09['within15'] = sum(1 for g in c09['all'] if g <= 15)
del c09['all']
out['c09'] = c09


# ------------------------------------------------------------------ 10. from the BOPA to entry into force
def vac(l):
    d = (D(l['inf']) - D(l['pub'])).days
    b = l['basis']
    if b.startswith('publication date'):
        return 'pre'
    if b.startswith('general rule'):
        return 'gen'
    if d <= 0:
        return 'same'
    if d == 1:
        return 'next'
    if d <= 31:
        return 'short'
    return 'long'


VK = ['same', 'next', 'short', 'gen', 'long', 'pre']
c10 = {'years': {}, 'keys': VK, 'long': []}
for y in YEARS:
    c10['years'][y] = {k: sum(1 for l in LAWLIKE if l['y'] == y and vac(l) == k) for k in VK}
c10['tot'] = {k: sum(1 for l in LAWLIKE if vac(l) == k) for k in VK}
c10['long'] = [[l['f'], l['t'], l['pub'], l['inf'], (D(l['inf']) - D(l['pub'])).days, l['br']] for l in
               sorted((l for l in LAWLIKE if vac(l) == 'long'), key=lambda l: -(D(l['inf']) - D(l['pub'])).days)]
c10['basis'] = dict(Counter(l['basis'] for l in LAWLIKE))
out['c10'] = c10

# ------------------------------------------------------------------ 11. the anatomy of a new law
c11 = {'periods': []}
for p0, p1 in PER:
    ls = [l for l in NEW if p0 <= l['y'] <= p1]
    mean = lambda k: statistics.mean(l['n'].get(k, 0) for l in ls)
    c11['periods'].append({'p': [p0, p1], 'n': len(ls), 'add': mean('add'), 'trans': mean('trans'), 'derog': mean('derog'), 'final': mean('final'),
                           'art': statistics.median(l['n'].get('art', 0) for l in ls), 'motius': statistics.median(l['motius'] for l in ls),
                           'has_motius': sum(1 for l in ls if l['motius'] > 30),
                           'share_words': {k: sum(l['w'].get(k, 0) for l in ls) for k in ('motius', 'art', 'add', 'trans', 'derog', 'final', 'annex')}})
out['c11'] = c11

# ------------------------------------------------------------------ 12. the wording of the entry-into-force clause
c12 = {'years': {}}
for y in YEARS:
    qs = [l['quote'] for l in LAWLIKE if l['y'] == y and l['quote']]
    c12['years'][y] = {'n': len(qs), 'present': sum(1 for q in qs if re.search(r"\bLa present Llei\b", q)),
                       'aquesta': sum(1 for q in qs if re.search(r"\bAquesta Llei\b", q, re.I)),
                       'fut': sum(1 for q in qs if re.search(r"\bentrar[àa]\b", q)), 'pres': sum(1 for q in qs if re.search(r"\bentra\b", q) and not re.search(r"\bentrar[àa]\b", q)),
                       'endema': sum(1 for q in qs if re.search(r"\bl'endemà\b|\bl’endemà\b", q))}
c12['n'] = sum(v['n'] for v in c12['years'].values())
c12['last_present'] = max((l['pub'] for l in LAWLIKE if re.search(r"\bLa present Llei\b", l['quote'])), default=None)
c12['last_present_t'] = next((l['t'] for l in LAWLIKE if l['pub'] == c12['last_present'] and re.search(r"\bLa present Llei\b", l['quote'])), None)
c12['text'] = {'present': sum(l['pres'].get('la_present', 0) for l in LAWLIKE), 'aquesta': sum(l['pres'].get('aquesta', 0) for l in LAWLIKE)}
out['c12'] = c12

# ------------------------------------------------------------------ 13. the changes later laws state, by year
c13 = {'years': {}, 'n': len(CH)}
for y in YEARS:
    rows = [c for c in CH if L[c[0]]['y'] == y]
    srcs = {c[0] for c in rows}
    c13['years'][y] = {'rows': len(rows), 'laws': len(srcs), 'titled': sum(1 for l in LAWLIKE if l['y'] == y and l['kind'] == 'amend'),
                       'titled_with': sum(1 for f in srcs if L[f]['kind'] == 'amend'),
                       'other_with': sum(1 for f in srcs if L[f]['kind'] != 'amend'),
                       'final': sum(1 for c in rows if c[3] in ('final', 'add', 'trans', 'derog')),
                       'ra': sum(1 for c in rows if L[c[0]]['kind'] == 'amend'),
                       'kinds': dict(Counter(c[2] for c in rows))}
c13['by_file'] = dict(Counter(c[3] for c in CH))
c13['by_kind'] = dict(Counter(c[2] for c in CH))
c13['by_src_kind'] = dict(Counter(L[c[0]]['kind'] for c in CH))
out['c13'] = c13

# ------------------------------------------------------------------ 14. the laws changed most often
tg = defaultdict(lambda: {'rows': 0, 'laws': set(), 'kinds': Counter(), 'years': Counter()})
for src, t, k, fk, _w in CH:
    if not t:
        continue
    g = tg[t]
    g['rows'] += 1
    g['laws'].add(src)
    g['kinds'][k] += 1
    g['years'][L[src]['y']] += 1
top = sorted(tg.items(), key=lambda kv: (-len(kv[1]['laws']), -kv[1]['rows']))[:15]
c14 = {'top': [[f, L[f]['t'], L[f]['ad'] or L[f]['pub'], len(g['laws']), g['rows'], dict(g['kinds']), sorted({L[s]['y'] for s in g['laws']})] for f, g in top],
       'targets': len(tg), 'resolved': sum(1 for c in CH if c[1]), 'unresolved': sum(1 for c in CH if not c[1]), 'n': len(CH)}
out['c14'] = c14

# ------------------------------------------------------------------ 15. how many laws a later law changes, by year of publication
c15 = {'years': {}}
for y in YEARS:
    ls = [l for l in LAWLIKE if l['y'] == y and l['kind'] in ('new', 'consol')]
    hit = [l for l in ls if l['f'] in tg]
    c15['years'][y] = {'n': len(ls), 'amended': len(hit), 'q': sum(1 for l in hit if l['q'])}
c15['n'] = sum(v['n'] for v in c15['years'].values())
c15['amended'] = sum(v['amended'] for v in c15['years'].values())
out['c15'] = c15

# ------------------------------------------------------------------ 16. consolidated texts
CONS = sorted((l for l in LAWLIKE if l['kind'] == 'consol'), key=lambda l: l['ad'] or l['pub'])
SW = {'de', 'del', 'dels', 'la', 'les', 'el', 'els', 'i', 'a', 'al', 'per', 'en', 'l', 'd', 'sobre', 'amb', 'qualificada'}


def toks(c):
    return {w for w in re.split(r"[ ']+", c) if w and w not in SW}


def sim(c1, c2):
    a_, b_ = toks(c1), toks(c2)
    return len(a_ & b_) / max(1, len(a_ | b_))


# the text consolidated, where its name changed: Llei 32/2021 says it consolidates the 'Llei de cooperació penal
# internacional i de lluita contra el blanqueig ..., del 29 de desembre del 2000', renamed (its statement of reasons)
ORIG_OVERRIDE = {'lleis/2021-032': 'lleis/2001-01-23-201a6'}
c16 = {'texts': []}
for l in CONS:
    c = l['core']
    pool = [x for x in L.values() if x['pub'] < l['pub'] and x['kind'] in ('new', 'const') and x['f'] != l['f']]
    best = max((sim(c, x['core']) for x in pool), default=0)
    cands = sorted((x for x in pool if best >= 0.6 and sim(c, x['core']) == best), key=lambda x: x['pub'])
    orig = L[ORIG_OVERRIDE[l['f']]] if l['f'] in ORIG_OVERRIDE else (cands[-1] if cands else None)
    # earlier consolidated text of the same law (the notariat twice): the original is the first text
    if orig:
        chain = [orig['f']] + [x['f'] for x in CONS if x['core'] == c and x['pub'] < l['pub']]
        am = sorted({src for src, t, k, fk, _w in CH if t in chain and L[src]['pub'] < l['pub'] and src not in chain})
    else:
        chain, am = [], []
    c16['texts'].append({'f': l['f'], 't': l['t'], 'ad': l['ad'], 'pub': l['pub'], 'q': l['q'], 'words': l['words'], 'obj': l['objection'],
                         'orig': [orig['f'], orig['t'], orig['ad'] or orig['pub']] if orig else None,
                         'prev': [x['f'] for x in CONS if x['core'] == c and x['pub'] < l['pub']],
                         'am': [[s, L[s]['t'], L[s]['ad'] or L[s]['pub']] for s in am]})
out['c16'] = c16
print('consolidated', [(x['t'][:50], x['orig'][1][:40] if x['orig'] else None, len(x['am'])) for x in c16['texts']])

# ------------------------------------------------------------------ 17. budgets and credit laws
c17 = {'budgets': {}, 'credit': {}, 'missing': []}
for l in LAWLIKE:
    mm = ANNUAL.search(l['t'])
    if mm and l['kind'] == 'budget':
        fy = int(mm.group(1))
        if fy not in c17['budgets'] or (l['ad'] or '') < c17['budgets'][fy]['ad']:
            c17['budgets'][fy] = {'f': l['f'], 't': l['t'], 'ad': l['ad'], 'pub': l['pub'], 'days': (D(l['ad']) - dt.date(fy, 1, 1)).days}
for y in YEARS:
    c17['credit'][y] = sum(1 for l in LAWLIKE if l['y'] == y and l['kind'] == 'credit')
    if y not in c17['budgets']:
        c17['missing'].append(y)
c17['n_credit'] = sum(c17['credit'].values())
c17['extraordinary'] = [[l['f'], l['t'], l['ad']] for l in LAWLIKE if l['kind'] == 'budget' and not ANNUAL.search(l['t'])]
out['c17'] = c17
print('budgets', len(c17['budgets']), 'missing', c17['missing'], 'before 1 Jan', sum(1 for b in c17['budgets'].values() if b['days'] < 0))

# ------------------------------------------------------------------ 18. taxes
TAXES = [
    ('consum', r"\btarifa general de taxes|\btaxes? (?:sobre el|al|de) consum|\bllei de taxes sobre el consum"),
    ('imi', r"\bimpost de mercaderies indirect|\bIMI\b"),
    ('canon', r"\bcànon sobre el consum d'electricitat"),
    ('vehicles', r"\btaxa sobre la tinença de vehicles"),
    ('registre', r"\btaxa sobre el Registre de Titulars d'Activitats Econòmiques"),
    ('bases', r"\bbases de l'ordenament tributari"),
    ('sectorials', r"\bimpost indirecte sobre (?:la prestació de serveis|la producció interna|les activitats comercials)|\bmòduls aplicables a les entitats bancàries"),
    ('plusv', r"\bimpost sobre (?:les )?plusvàlues"),
    ('itp', r"\bimpost sobre (?:les )?transmissions patrimonials immobiliàries"),
    ('especials', r"\bimpostos especials"),
    ('irnr', r"\brenda dels no.residents"),
    ('is', r"\bimpost sobre societats"),
    ('irae', r"\brenda de les activitats econòmiques"),
    ('igi', r"\bimpost general indirecte"),
    ('irpf', r"\brenda de les persones físiques"),
    ('turist', r"\bestades en allotjaments turístics"),
    ('iei', r"\binversió estrangera immobiliària"),
]
TAX_RX = [(k, re.compile(rx, re.I)) for k, rx in TAXES]


def tax_of_title(t):
    return [k for k, rx in TAX_RX if rx.search(t)]


TAXLAW = {}       # folder -> the tax its own title regulates: the title up to ', de modificació ...' names it
EMPTY_HEAD = re.compile(r"^[Ll]lei(?:\s+qualificada)?(?:\s+\d{1,3}\s*[/-]\s*\d{2,4},?\s+(?:del?\s+|de l')\d{1,2}\s+(?:de\s+|d')\w+)?,?\s*$")
for l in LAWLIKE:
    head = re.split(r",?\s+(?:i\s+)?de modificaci[óo]\b", l['t'])[0]
    ks = tax_of_title(head)
    if ks and l['kind'] in ('new', 'amend') and not CREDIT.search(l['t']) and not EMPTY_HEAD.match(head):
        TAXLAW[l['f']] = ks[0]
c18 = {'keys': [k for k, _ in TAXES], 'rows': {}}
for k in c18['keys']:
    created = sorted((L[f] for f, kk in TAXLAW.items() if kk == k), key=lambda l: l['pub'])
    created_f = {l['f'] for l in created}
    touch = defaultdict(set)
    for l in LAWLIKE:   # laws whose title names the tax as what they change
        if l['f'] in created_f:
            continue
        if k in tax_of_title(l['t']) and l['kind'] in ('amend', 'new', 'budget') and not CREDIT.search(l['t']):
            touch[int((l['ad'] or l['pub'])[:4])].add(l['f'])
    for src, t, kind, fk, _w in CH:   # laws that state changes to the tax's own law
        if t in created_f and src not in created_f:
            touch[int((L[src]['ad'] or L[src]['pub'])[:4])].add(src)
    c18['rows'][k] = {'created': [[l['f'], l['t'], l['ad'] or l['pub'], int((l['ad'] or l['pub'])[:4])] for l in created],
                      'touch': {y: sorted(v) for y, v in touch.items()}, 'n': len({f for v in touch.values() for f in v})}
c18['names'] = {f: L[f]['t'] for k in c18['rows'] for v in c18['rows'][k]['touch'].values() for f in v}
out['c18'] = c18
print('taxes', {k: (len(v['created']), v['n']) for k, v in c18['rows'].items()})

# ------------------------------------------------------------------ 19. currencies
c19 = {'years': {}}
for y in YEARS:
    ls = [l for l in LAWLIKE if l['y'] == y]
    c19['years'][y] = {'n': len(ls), 'pta': sum(1 for l in ls if l['m'].get('pta')), 'eur': sum(1 for l in ls if l['m'].get('eur')),
                       'frf': sum(1 for l in ls if l['m'].get('frf')), 'ecu': sum(1 for l in ls if l['m'].get('ecu'))}
c19['first_eur'] = min((l['pub'] for l in LAWLIKE if l['m'].get('eur')), default=None)
c19['first_eur_t'] = next((l['t'] for l in sorted(LAWLIKE, key=lambda l: l['pub']) if l['m'].get('eur')), None)
lp = sorted((l for l in LAWLIKE if l['m'].get('pta')), key=lambda l: l['pub'])
c19['pta_laws'] = len(lp)
c19['pta_after2002'] = [[l['f'], l['t'], l['pub']] for l in lp if l['y'] > 2002]
c19['last_pta_main'] = [lp[i]['t'] for i in range(len(lp)) if lp[i]['y'] <= 2002][-1:]
c19['frf_laws'] = [[l['f'], l['t'], l['pub']] for l in LAWLIKE if l['m'].get('frf')]
c19['euro_law'] = [[l['f'], l['t'], l['pub']] for l in LAWLIKE if re.search(r"transició cap a l'euro", l['t'])]
out['c19'] = c19

# ------------------------------------------------------------------ 20. Europe and international bodies
BODIES = [('eu', ['eu', 'ec']), ('acts', ['dir', 'reg']), ('monetari', ['monetari']), ('coe', ['coe']), ('onu', ['onu']), ('ocde', ['ocde']), ('gafi', ['gafi', 'moneyval'])]
c20 = {'periods': [[p0, p1] for p0, p1 in PER5], 'bodies': [k for k, _ in BODIES], 'cells': {}, 'ptot': c02['ptot'], 'dirs': []}
for k, keys in BODIES:
    c20['cells'][k] = [sum(1 for l in LAWLIKE if p0 <= l['y'] <= p1 and any(l['m'].get(x) for x in keys)) for p0, p1 in PER5]
c20['tot'] = {k: sum(1 for l in LAWLIKE if any(l['m'].get(x) for x in keys)) for k, keys in BODIES}
c20['dirlaws'] = [[l['f'], l['t'], l['y'], len(l['dirs'])] for l in sorted((l for l in LAWLIKE if l['dirs']), key=lambda l: (-len(l['dirs']), l['pub']))]
c20['n_dirs'] = len({d for l in LAWLIKE for d in l['dirs']})
c20['first_monetari'] = next(([l['f'], l['t'], l['pub']] for l in sorted(LAWLIKE, key=lambda l: l['pub']) if l['m'].get('monetari')), None)
out['c20'] = c20

# ------------------------------------------------------------------ profile
qn = len(QL)
PF = {'acts': len(ACTS), 'lawlike': len(LAWLIKE), 'docs': len(ACTS) - len(LAWLIKE), 'qualified': qn, 'main': sum(1 for l in ACTS if l['br'] == 'main'),
      'future': sum(1 for l in ACTS if l['br'] == 'future'), 'files': sum(sum(l['n'].values()) for l in L.values()),
      'articles': sum(l['n'].get('art', 0) for l in L.values()), 'words': sum(l['words'] for l in LAWLIKE) + L['constitucio']['words'],
      'changes': len(CH), 'amend_rows': len(AM), 'corrections': len(CORR), 'first_pub': STATS.get('first_published'), 'last_pub': LAST_PUB,
      'record_to': RECORD_TO, 'built': BUILT, 'head': a.ref_sha, 'future_head': a.future_sha, 'commits': STATS.get('commits_main'),
      'consolidated': len(CONS), 'signed': len(POST), 'units': STATS.get('units'),
      'corrections_list': [[c['title'], c['published']] for c in CORR], 'unresolved': c14['unresolved']}
out_all = {'profile': PF, 'charts': out, 'titles': {l['f']: [l['t'], l['ad'] or l['pub']] for l in L.values() if l['kind'] != 'doc'}}
json.dump(out_all, open(os.path.join(B, 'data.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'), default=list)
print('data.json', os.path.getsize(os.path.join(B, 'data.json')))
