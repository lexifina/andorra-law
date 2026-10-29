"""Print an Andorran law, or one article of it, as this repository has it on a date.

    python tools/in_force_on.py 2026-10-01 lleis/2022-041                  # the whole law, in order
    python tools/in_force_on.py 2026-10-01 lleis/2022-041 article-002      # one article
    python tools/in_force_on.py 1993-06-01 constitucio article-001

Reads the `In-force:` trailers. Each law here is its text as enacted (the BOPA publishes no consolidations with
dated past versions), so the answer is the text as enacted if the law had entered into force by that date, and
nothing before. Later amendments are NOT applied: the text printed may have been changed or repealed since; see
data/amendments.csv for the changes later laws state. Laws that enter into force after the build date are on the
branch `future`, which this tool also reads. Standard library only.
"""
import subprocess
import sys


def git(*args: str) -> str:
    return subprocess.run(['git', *args], capture_output=True, text=True, encoding='utf-8', check=True).stdout


def has(ref: str) -> bool:
    return subprocess.run(['git', 'rev-parse', '--verify', '-q', ref], capture_output=True).returncode == 0


def commit_on(day: str, path: str) -> tuple[str | None, str | None]:
    """The last commit with an In-force date on or before `day` that touched `path`, and the earliest date known."""
    ref = 'future' if has('refs/heads/future') else 'main'
    fmt = '%H%x1f%(trailers:key=In-force,valueonly,separator=)'
    earliest = None
    for line in git('log', '--first-parent', f'--format={fmt}', ref, '--', path).splitlines():
        h, d = (line.split('\x1f') + [''])[:2]
        d = d.strip()
        if not d:
            continue
        earliest = d
        if d <= day:
            return h, d
    return None, earliest


def main() -> None:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day, law = sys.argv[1], sys.argv[2].strip('/')
    unit = sys.argv[3] if len(sys.argv) > 3 else None
    if unit and unit.endswith('.md'):
        unit = unit[:-3]
    path = f'{law}/{unit}.md' if unit else law
    h, when = commit_on(day, path)
    if not h:
        if when:
            sys.exit(f'{path}: not yet in force on {day}; it enters into force on {when} (as enacted)')
        sys.exit(f'{path}: not found')
    sys.stderr.write(f'{path}: as enacted, in force from {when}; later amendments are not applied '
                     f'(see data/amendments.csv)\n')
    if unit:
        sys.stdout.write(git('show', f'{h}:{path}'))
        return
    names = [n for n in git('show', f'{h}:{law}/index.txt').splitlines() if n]
    for n in names:
        sys.stdout.write(git('show', f'{h}:{law}/{n}') + '\n')


if __name__ == '__main__':
    main()
