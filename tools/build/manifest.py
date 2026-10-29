"""Where each BOPA document of the manifest (the list of documents under the themes "Lleis" and "Constitucio") is read
from: one entry per document, and the file of its whole text. Used by build.py and docs.py.
"""
from pathlib import Path

HERE = Path(__file__).parent
CACHE = HERE / '.cache'
DOCS = CACHE / 'docs'


def full_url(d: dict) -> str:
    """The address of a document's whole text. The search indexes long documents as chunks (fileType htmlCopy,
    named `<k>_<nomDocument>.html`, ~128 KB each); the whole file sits beside them as `<nomDocument>.html`."""
    url = d['metadata_storage_path']
    return url.rsplit('/', 1)[0] + '/' + d['nomDocument'] + '.html'


def doc_key(d: dict) -> tuple[str, str]:
    return d['metadata_storage_path'].rsplit('/', 3)[-3], d['nomDocument']


def unique_docs(items: list[dict]) -> list[dict]:
    """One entry per document (a chunked document is listed once per chunk the search returned)."""
    seen, out = set(), []
    for d in items:
        if doc_key(d) not in seen:
            seen.add(doc_key(d))
            out.append(d)
    return out


def doc_path(d: dict) -> Path:
    folder, name = doc_key(d)
    return DOCS / folder / (name + '.html')
