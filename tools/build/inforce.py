"""Dates for the Andorra build: the local clock, Catalan dates and numbers, and each law's in-force date read from its
own final provisions."""
import re
from datetime import date, datetime, timedelta, timezone

MONTHS = {'gener': 1, 'febrer': 2, 'març': 3, 'marc': 3, 'abril': 4, 'maig': 5, 'juny': 6, 'juliol': 7, 'agost': 8,
          'setembre': 9, 'octubre': 10, 'novembre': 11, 'desembre': 12}

UNITS = {'un': 1, 'u': 1, 'una': 1, 'dos': 2, 'dues': 2, 'tres': 3, 'quatre': 4, 'cinc': 5, 'sis': 6, 'set': 7,
         'vuit': 8, 'nou': 9, 'deu': 10, 'onze': 11, 'dotze': 12, 'tretze': 13, 'catorze': 14, 'quinze': 15,
         'setze': 16, 'disset': 17, 'divuit': 18, 'dinou': 19, 'vint': 20, 'trenta': 30, 'quaranta': 40,
         'cinquanta': 50, 'seixanta': 60, 'noranta': 90, 'cent': 100}


def number(word: str) -> int | None:
    """A cardinal written in digits or Catalan words ("quinze", "vint-i-un", "trenta-dos")."""
    w = word.lower().strip()
    if w.isdigit():
        return int(w)
    if w in UNITS:
        return UNITS[w]
    m = re.fullmatch(r'(vint)-i-(\w+)', w) or re.fullmatch(r'(trenta|quaranta|cinquanta|seixanta|noranta)-(\w+)', w)
    if m and m.group(2) in UNITS and UNITS[m.group(2)] < 10:
        return UNITS[m.group(1)] + UNITS[m.group(2)]
    return None


NUM = r'(\d{1,3}|[a-zà-ú]+(?:-i-[a-zà-ú]+|-[a-zà-ú]+)?)'
DATE_RX = re.compile(r"\b(?:el\s+|l[’']\s*)?(?:dia\s+)?(\d{1,2}|1r|primer)(?:\s+de|\s+d[’'])\s*(" + '|'.join(MONTHS) +
                     r")\s+(?:de|del)\s+(?:l[’']any\s+)?((?:19|20)\d\d)\b", re.I)


def catalan_date(text: str) -> date | None:
    m = DATE_RX.search(text)
    if not m:
        return None
    d = 1 if m.group(1).lower() in ('1r', 'primer') else int(m.group(1))
    try:
        return date(int(m.group(3)), MONTHS[m.group(2).lower()], d)
    except ValueError:
        return None


def add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    m += 1
    for day in (d.day, 30, 29, 28):
        try:
            return date(y, m, day)
        except ValueError:
            continue
    raise ValueError(d)


SUBJECT = re.compile(r"(?:aquesta|present|aquest)\s+(?:llei|constitució|codi|text)", re.I)
SUBJECT_START = re.compile(r"\W*(?:la|el)\s+(?:llei|constitució|codi)\b(?!\s+(?:\d|qualificada\s+\d))", re.I)
VIGOR = re.compile(r'(?:entra(?:rà|ran|n)?|entraran|entrarà)\s+en\s+vigor', re.I)


def in_force(sentences: list[str], published: date) -> tuple[date | None, str, str]:
    """(day, basis, quoted sentence) from the first sentence that says when the law (as a whole) enters into force.
    basis is one of: next day, N days, N months, publication day, explicit date."""
    for s in sentences:
        m = VIGOR.search(s)
        if not m:
            continue
        rest = s[m.end():m.end() + 220]
        # the clause ends where the gazette is named ("... publicació al Butlletí Oficial ...")
        cut = re.search(r'Butllet|BOPA|[;:]|,\s*(?:excepte|llevat|amb\s+excepció|tret)', rest)
        clause = rest[:cut.start()] if cut else rest
        clause = re.sub(r'\(\s*\d+\s*\)', ' ', clause)
        low = clause.lower()
        quote = s.strip()[:400]
        if not re.search(r'\w', low):
            continue
        # the subject must be this law ("Aquesta Llei", "La present Llei qualificada ...", "Aquesta Constitució")
        before = s[max(0, m.start() - 220):m.start()]
        if not (SUBJECT.search(before) or SUBJECT_START.match(s[:m.start()]) or re.match(r'\s*(?:[-–]\s*)?$', s[:m.start()])):
            continue
        mm = re.search(r"primer\s+dia\s+(?:natural\s+)?del\s+mes\s+de\s+(" + '|'.join(MONTHS) + r")\s+(?:de|del)\s+(?:l[’']any\s+)?((?:19|20)\d\d)", low)
        if mm:
            return date(int(mm.group(2)), MONTHS[mm.group(1)], 1), 'a date it names', quote
        mm = re.search(r"\b" + NUM + r"\s+(dies|mesos|mes|anys|any)\b", low)
        if mm and number(mm.group(1)):
            n = number(mm.group(1))
            unit = mm.group(2)
            if unit.startswith('di'):
                return published + timedelta(days=n), f'{n} days after publication', quote
            if unit.startswith('mes'):
                return add_months(published, n), f'{n} months after publication', quote
            return add_months(published, 12 * n), f'{n} years after publication', quote
        mm = re.search(r"\b(un|una)\s+(mes|any)\b", low)
        if mm:
            return add_months(published, 1 if mm.group(2) == 'mes' else 12), f'1 {mm.group(2)} after publication', quote
        if re.search(r"endemà|endema|dia\s+següent|l[’']\s*endem", low):
            return published + timedelta(days=1), 'the day after publication', quote
        d = catalan_date(clause[:140])
        if d:
            return d, 'a date it names', quote
        mm = re.search(r"\b(\d{1,2}|1r|primer)\s+(?:de\s+|d['’])(" + '|'.join(MONTHS) + r")\s+d['’]enguany", low)
        if mm:
            day = 1 if mm.group(1) in ('1r', 'primer') else int(mm.group(1))
            return date(published.year, MONTHS[mm.group(2)], day), 'a date it names (this year)', quote
        if re.search(r"publi(?:cació|cacio|cada|cat|ca|qui|quin|quen|car-se|car)\b", low):
            return published, 'the day of publication', quote
    return None, '', ''


# ------------------------------------------------------------------------------------------- the local clock

def last_sunday(y: int, m: int) -> date:
    d = date(y, m, 31) if m in (3, 10, 12, 1, 5, 7, 8) else date(y, m, 30)
    return d - timedelta(days=(d.weekday() + 1) % 7)


def utc_offset(day: date) -> int:
    """Andorra keeps Central European Time with the EU summer-time rules (from 1985 here, as in Spain and France):
    summer time from the last Sunday of March to the last Sunday of September until 1995, of October from 1996.
    Minutes east of UTC at noon on `day` (the change happens at 01:00 UTC, before noon)."""
    if day.year < 1985:
        return 60
    end = last_sunday(day.year, 9 if day.year <= 1995 else 10)
    return 120 if last_sunday(day.year, 3) <= day < end else 60


def local_date(stamp: str) -> date:
    """The local calendar day of a BOPA timestamp ("1989-01-29T11:00:00+00:00", midnight local in UTC)."""
    t = datetime.fromisoformat(stamp).astimezone(timezone.utc)
    d = t.date()
    t2 = t + timedelta(minutes=utc_offset(d))
    return t2.date()


def git_date(day: str) -> str:
    d = date.fromisoformat(day)
    off = utc_offset(d)
    ts = int((datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc) - timedelta(minutes=off)).timestamp())
    return f'{ts} +{off // 60:02d}{off % 60:02d}'
