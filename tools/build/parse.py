"""Turn one BOPA document (UTF-16 HTML) into paragraphs, then into units (preamble, articles, dispositions, annexes,
signatures).

Two kinds of HTML come from the BOPA:
- up to about 2015, the text sits in one table cell, one printed line per `<br>` (hard-wrapped at the gazette's
  column). The lines are joined back into paragraphs: a line ends its paragraph when the next line's first word would
  have fitted on it (so the break was the author's, not the column's), or when the next line starts a heading.
  A line ending in a hyphen is joined without a space (the hyphens are Catalan's own, "comunicar-|les").
- from about 2015, one `<p class="...">` per paragraph (Titol-3 title, Titol-5/6/7 headings, Body-text...).
Tables become one line per row, cells separated by " | ". The links the BOPA site adds later ("Text refós",
"Descarrega el document") are not part of the law and are dropped (counted in `dropped`).
"""
import html
import re
from html.parser import HTMLParser

BLOCK = {'p', 'div', 'table', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'body', 'html', 'pre'}
SITE_LINKS = ('Text refós', 'Descarrega el document', 'Text refos')
SITE_LINK_RX = re.compile(r'Text refós|Descarrega el document', re.I)


class Blocks(HTMLParser):
    """Blocks of lines: each block is (css class, [lines]); a table row with several cells is one line."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, list[str]]] = []
        self.lines: list[str] = []
        self.cur: list[str] = []
        self.cls = ''
        self.row: list[str] | None = None
        self.cell: list[str] | None = None
        self.rows_cells: list[list[str]] = []
        self.skip = 0
        self.anchor: list[str] | None = None
        self.dropped: list[str] = []
        self.amarks: list[tuple[list, int]] = []

    # -- text
    def _text(self, s: str) -> None:
        if self.skip:
            return
        if self.anchor is not None:
            self.anchor.append(s)
        if self.cell is not None:
            self.cell.append(s)
        else:
            self.cur.append(s)

    def handle_data(self, data: str) -> None:
        self._text(data.replace('\r', '').replace('\n', ' '))

    def _endline(self) -> None:
        line = ''.join(self.cur)
        self.cur = []
        self.lines.append(line)

    def _endblock(self) -> None:
        if self.cur:
            self._endline()
        lines = [re.sub(r'[ \t ]+', ' ', l).strip() for l in self.lines]
        while lines and not lines[-1]:
            lines.pop()
        while lines and not lines[0]:
            lines.pop(0)
        if lines:
            self.blocks.append((self.cls, lines))
        self.lines = []

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        if tag in ('script', 'style', 'head', 'title'):
            self.skip += 1
            return
        if tag == 'a':
            target = self.cell if self.cell is not None else self.cur
            self.amarks.append((target, len(target)))
            self.anchor = []
        if tag == 'br':
            if self.cell is not None:
                self.cell.append('\n')
            else:
                self._endline()
            return
        if tag == 'tr':
            if self.cell is not None:
                # a table inside the old layout's one cell: what the cell holds so far is text, flushed first
                self._endblock()
                self.lines = ''.join(self.cell).split('\n')
                self.cls = ''
                self._endblock()
                self.cell = None
            self.row = []
            return
        if tag in ('td', 'th'):
            self.cell = []
            return
        if tag in BLOCK and self.cell is not None and tag not in ('table', 'body', 'html'):
            # a paragraph inside the old layout's one table cell (often an unclosed <p>): a hard break
            self.cell.append('\n\n')
            return
        if tag in BLOCK:
            self._endblock()
            if tag == 'p':
                self.cls = (a.get('class') or '').split(' ')[0]

    def handle_startendtag(self, tag, attrs) -> None:
        if tag == 'br':
            self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in ('script', 'style', 'head', 'title'):
            self.skip = max(0, self.skip - 1)
            return
        if tag == 'a' and self.anchor is not None:
            text = re.sub(r'\s+', ' ', ''.join(self.anchor)).strip()
            target, mark = self.amarks.pop() if self.amarks else (None, 0)
            if SITE_LINK_RX.search(text):
                self.dropped.append(text)
                # the link is the site's, not the law's: take its words back out of the text
                now = self.cell if self.cell is not None else self.cur
                if target is now and len(now) >= mark:
                    del now[mark:]
            if not self.amarks:
                self.anchor = None
            return
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(''.join(self.cell)) if self.row is not None else None
            self.cell = None
            return
        if tag == 'tr' and self.row is not None:
            row, self.row = self.row, None
            if len(row) == 1:
                # a one-cell row is the old layout's container: its lines are text lines
                self._endblock()
                self.lines = row[0].split('\n')
                self.cls = ''
                self._endblock()
            else:
                cells = [re.sub(r'\s+', ' ', c).strip() for c in row]
                if any(cells):
                    self._endblock()
                    self.lines = [' | '.join(cells)]
                    self.cls = 'table-row'
                    self._endblock()
            return
        if tag in BLOCK:
            self._endblock()
            self.cls = ''

    def close(self) -> None:
        super().close()
        self._endblock()


def decode(raw: bytes) -> str:
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return raw.decode('utf-16')
    if raw[:3] == b'\xef\xbb\xbf':
        return raw[3:].decode('utf-8')
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('cp1252')


ORD_WORDS = ('primer|primera|segon|segona|tercer|tercera|quart|quarta|cinquè|cinquena|sisè|sisena|setè|setena|vuitè|vuitena|'
             'novè|novena|desè|desena|onzè|onzena|dotzè|dotzena|tretzè|tretzena|catorzè|catorzena|quinzè|quinzena|'
             'setzè|setzena|dissetè|dissetena|divuitè|divuitena|dinovè|dinovena|vintè|vintena|únic|única|unic|unica|'
             'preliminar')
MARKER = re.compile(
    r'^(?:Article\s+(?:\d+|únic|unic)\b|Art\.\s*\d+|Disposici(?:ó|ons)\s+(?:addicional|transitòria|transitoria|derogatòria|derogatoria|final|adicional)'
    r'|(?:Títol|Titol|Capítol|Capitol|Secció|Seccio|Subsecció|Llibre|Part)\s+(?:[IVXLC]+|\d+|' + ORD_WORDS + r')\b'
    r'|Annex(?:os)?\b|Exposició de motius|Preàmbul|Casa de la Vall,)', re.I)


NUMBERED = re.compile(r'^(?:\d{1,3}[.)]|[a-z]\)|[a-z]\.|[-–—•]|\d{1,3}\.\d{1,3}\.?)\s')


def reflow(lines: list[str]) -> list[str]:
    """Join hard-wrapped lines back into paragraphs (see the module docstring)."""
    if len(lines) < 8:
        return lines
    lengths = sorted(len(l) for l in lines if l)
    width = lengths[int(len(lengths) * 0.9)] if lengths else 0
    out: list[str] = []
    cur = ''
    for i, line in enumerate(lines):
        if not line:
            if cur:
                out.append(cur)
                cur = ''
            continue
        if cur:
            prev = prev_line
            first = line.split(' ', 1)[0]
            fitted = len(prev) + 1 + len(first) <= width
            numbered = prev.endswith(('.', ':', ';')) and NUMBERED.match(line)
            if fitted or numbered or MARKER.match(line) or ' | ' in line or ' | ' in prev:
                out.append(cur)
                cur = line
            elif prev.endswith('-') and not prev.endswith(' -'):
                cur += line
            else:
                cur += ' ' + line
        else:
            cur = line
        prev_line = line
    if cur:
        out.append(cur)
    return out


def paragraphs(raw: bytes) -> tuple[list[tuple[str, str]], list[str]]:
    """[(css class, paragraph)] and the dropped site links."""
    p = Blocks()
    p.feed(decode(raw))
    p.close()
    out = []
    for cls, lines in p.blocks:
        if cls in ('', 'table-row') and len(lines) >= 8:
            lines = reflow(lines)
        for l in lines:
            l = l.strip()
            if l and l not in SITE_LINKS and l not in p.dropped:
                out.append((cls, l))
    return out, p.dropped


# ------------------------------------------------------------------------------------------------ units

ORD = {'primer': 1, 'primera': 1, 'segon': 2, 'segona': 2, 'tercer': 3, 'tercera': 3, 'quart': 4, 'quarta': 4,
       'cinquè': 5, 'cinquena': 5, 'sisè': 6, 'sisena': 6, 'setè': 7, 'setena': 7, 'vuitè': 8, 'vuitena': 8,
       'novè': 9, 'novena': 9, 'desè': 10, 'desena': 10, 'onzè': 11, 'onzena': 11, 'dotzè': 12, 'dotzena': 12}
SUFFIX = ['', 'bis', 'ter', 'quater', 'quinquies', 'sexies', 'septies', 'octies', 'novies', 'nonies', 'decies']
ART_ORD = {w: i for i, w in enumerate('primer segon tercer quart cinquè sisè setè vuitè novè desè onzè dotzè tretzè '
                                        'catorzè quinzè setzè dissetè divuitè dinovè vintè'.split(), 1)}
ART_WORDS = '|'.join(ART_ORD)
ART = re.compile(r'^(?:Article|Art\.)\s*(\d+(?=[rntè]\b|\b)[rntè]?|únic|unic|' + ART_WORDS + r')\b(?:\s*(bis|ter|quater|quinquies|sexies|septies|octies|novies|nonies|decies)\b|\s*((?-i:[A-Z]))\b)?'
                 r'\s*(?:[.:\-–—)]|$|\s)', re.I)
DISP = re.compile(r'^Disposici(?:ó|ons)\s+(addicional|adicional|transitòria|transitoria|derogatòria|derogatoria|final)(s)?\b'
                  r'\s*([a-zàèéíòóúç]+(?:\s+bis)?)?', re.I)
STRUCT = re.compile(r'^(Títol|Titol|Capítol|Capitol|Secció|Seccio|Subsecció|Llibre|Part)\s+([IVXLC]+|\d+|' + ORD_WORDS + r')(?:[ªaº]|r|n)?\b', re.I)
ANNEX = re.compile(r'^Annex(?:os)?\b\s*([IVXLC]+|\d+|[A-Z])?\b', re.I)
SIGN = re.compile(r'^(?:Casa de la Vall|Perpinyà|Perpignan|La Seu d.Urgell|Andorra la Vella),?\s', re.I)
GROUP_ITEM = re.compile(r'^(' + ORD_WORDS + r')(?:\s*[.:\-–]\s*\S.*|\.)?$', re.I)
QUOTE = ('“', '"', '«', "'", '‘', '”')


def slug(s: str) -> str:
    s = s.lower()
    for a, b in (('à', 'a'), ('è', 'e'), ('é', 'e'), ('í', 'i'), ('ï', 'i'), ('ò', 'o'), ('ó', 'o'), ('ú', 'u'),
                 ('ü', 'u'), ('ç', 'c'), ('·', ''), ('l.l', 'll')):
        s = s.replace(a, b)
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


ORDINAL = re.compile(r'(?:' + slug(ORD_WORDS).replace('-', '|') + r'|[a-z]{3,}ena|[a-z]{3,}e|bis)(?:-bis)?')


def art_key(m: re.Match) -> tuple[int, int]:
    n = m.group(1).lower()
    num = 0 if n in ('únic', 'unic') else ART_ORD[n] if n in ART_ORD else int(n.rstrip('rntè'))
    suf = (m.group(2) or '').lower()
    if suf:
        return num, SUFFIX.index(suf) if suf in SUFFIX else 1
    if m.group(3):
        return num, ord(m.group(3).upper()) - 64
    return num, 0


def follows(a: tuple[int, int], b: tuple[int, int]) -> bool:
    """May article b come right after article a in a law's own numbering?"""
    if a[0] == 0 or b[0] == 0:
        return False
    if b[0] == a[0]:
        return b[1] > a[1]
    return b[0] == a[0] + 1 and b[1] == 0


def chain(cands: list[tuple[int, tuple[int, int]]]) -> list[int]:
    """The longest run of article headings numbered 1, 2, 2 bis, 3...; on a tie the later one (the body follows
    any table of contents). Returns positions in `cands`."""
    n = len(cands)
    best = [1] * n
    prev = [-1] * n
    for j in range(n):
        for i in range(j):
            if follows(cands[i][1], cands[j][1]) and best[i] + 1 >= best[j] and best[i] + 1 > 1:
                best[j], prev[j] = best[i] + 1, i
    if not n:
        return []
    top = max(best)
    # the chain should start at article 1 (or the first article); prefer the latest chain of maximal length
    end = max(j for j in range(n) if best[j] == top)
    out = []
    while end >= 0:
        out.append(end)
        end = prev[end]
    return out[::-1]


def units(paras: list[tuple[str, str]]) -> list[dict]:
    """Split paragraphs into units: [{'stem', 'kind', 'label', 'lines'}]. Headings above a unit (Títol, Capítol,
    Secció) are its first lines, as `## ...`; the unit's own heading is `# ...`."""
    texts = [t for _, t in paras]
    arts = [(i, art_key(m)) for i, t in enumerate(texts) if not t.startswith(QUOTE) and (m := ART.match(t))]
    unic = [i for i, t in enumerate(texts) if re.match(r'^Article\s+(únic|unic)\b', t, re.I) and not t.startswith(QUOTE)]
    picked = [arts[k][0] for k in chain([a for a in arts if a[1][0] > 0])]
    if len(picked) == 1 and unic:
        picked = []
    if not picked and unic:
        picked = [unic[-1]]
    is_art = set(picked)
    first = picked[0] if picked else None
    last_art = picked[-1] if picked else None
    # the body starts at the first article, moving back over the headings right above it
    start = first
    if start is not None:
        k = start
        while k > 0:
            t = texts[k - 1]
            if STRUCT.match(t) and not t.startswith(QUOTE):
                k -= 1
            elif k - 2 >= 0 and STRUCT.match(texts[k - 2]) and len(t) < 200 and not t.rstrip().endswith(('.', ':', ';')):
                k -= 2
            else:
                break
        start = k
    else:
        # no articles: dispositions after the preamble (laws made of one "Article únic" or dispositions only)
        ds = [i for i, t in enumerate(texts) if DISP.match(t) and not t.startswith(QUOTE)]
        start = ds[0] if ds else None
    out: list[dict] = []
    pre = texts[:start] if start is not None else texts
    out.append({'stem': 'preamble', 'kind': 'preamble', 'label': 'preamble', 'lines': list(pre)})
    if start is None:
        return out
    headings: list[str] = []
    cur: dict | None = None
    seen: dict[str, int] = {}
    after_sign = False
    heading_title = False
    group = ''  # the kind under a plural heading ("Disposicions finals"), whose items are "Primera", "Segona"...

    def new(stem: str, kind: str, label: str, head: str) -> dict:
        nonlocal headings
        if stem in seen:
            seen[stem] += 1
            stem = f'{stem}-{seen[stem]}'
        else:
            seen[stem] = 1
        u = {'stem': stem, 'kind': kind, 'label': label, 'lines': [f'## {h}' for h in headings] + [f'# {head}']}
        headings = []
        out.append(u)
        return u

    for i in range(start, len(texts)):
        t = texts[i]
        quoted = t.startswith(QUOTE)
        after_body = last_art is None or i > last_art
        if i in is_art:
            m = ART.match(t)
            num, suf = art_key(m)
            stem = 'article-unic' if num == 0 else f'article-{num:03d}' + (f'-{SUFFIX[suf]}' if 0 < suf < len(SUFFIX) and m.group(2) else (f'-{m.group(3).lower()}' if m.group(3) else ''))
            cur = new(stem, 'article', f"Article {m.group(1)}{(' ' + m.group(2)) if m.group(2) else ''}{(' ' + m.group(3)) if m.group(3) else ''}", t)
            heading_title = False
            continue
        if not quoted and after_body and (dm := DISP.match(t)) and not dm.group(2):
            kind = slug(dm.group(1)).replace('adicional', 'addicional')
            ordw = slug(dm.group(3) or '')
            ordw = ordw if ORDINAL.fullmatch(ordw) else ''
            stem = f'disposicio-{kind}' + (f'-{ordw}' if ordw else '')
            cur = new(stem, 'disposition', t.split('.')[0][:80], t)
            heading_title = False
            continue
        if not quoted and after_body and ANNEX.match(t) and len(t) < 200:
            m = ANNEX.match(t)
            stem = 'annex' + (f'-{slug(m.group(1))}' if m.group(1) else '')
            cur = new(stem, 'annex', t[:80], t)
            heading_title = False
            continue
        if not quoted and after_body and SIGN.match(t) and not after_sign:
            cur = new('signatures', 'signatures', 'signatures', t)
            after_sign = True
            continue
        if not quoted and after_body and group and (om := GROUP_ITEM.match(t)) and len(t) < 250:
            stem = f'disposicio-{group}-{slug(om.group(1))}'
            cur = new(stem, 'disposition', t[:80], t)
            heading_title = False
            continue
        if not quoted and (STRUCT.match(t) or (DISP.match(t) and DISP.match(t).group(2))) and len(t) < 250:
            if after_body and (dm := DISP.match(t)) and dm.group(2):
                group = slug(dm.group(1)).replace('adicional', 'addicional')
            headings.append(t)
            heading_title = bool(STRUCT.match(t)) and not re.search(r'[.:]\s*\S', t[len(STRUCT.match(t).group(0)):])
            continue
        if heading_title and headings and len(t) < 200 and not t.rstrip().endswith(('.', ';', ':')):
            headings.append(t)
            heading_title = False
            continue
        heading_title = False
        if headings:
            # headings with no unit after them before running text: keep them where they are
            (cur or out[0])['lines'].extend(f'## {h}' for h in headings)
            headings = []
        if cur is None:
            out[0]['lines'].append(t)
        else:
            cur['lines'].append(t)
    if headings:
        (cur or out[0])['lines'] += [f'## {h}' for h in headings]
    return out
