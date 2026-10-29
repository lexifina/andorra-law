# Sources

## The text

Butlletí Oficial del Principat d'Andorra (BOPA), https://www.bopa.ad, published by the Servei del Butlletí Oficial del
Principat d'Andorra. Every document listed by the BOPA's search under the themes "Lleis" (laws of the Consell General)
and "Constitució del Principat d'Andorra", from 1989 to {{TODAY}}: {{DOCUMENTS}} documents, of which {{LAWS_ALL}} laws
and the Constitution are built and {{CORRECTIONS}} are corrections of errata, listed only.

- Search: `POST https://bopaazurefunctions.azurewebsites.net/api/GetPaginatedDocuments2Indexes` (the request the
  website makes; its function key is in the website's own script), one query per theme and year.
- Documents: `https://bopadocuments.blob.core.windows.net/bopa-documents/<folder>/html/<id>.html` (UTF-16 HTML). The
  folder is the bulletin: the year counted from 1989 (001 = 1989) and the bulletin number.
- Retrieved {{FETCHED}}; the sha256 of every document read is in `data/source-sha256.tsv`.

## Robots, terms, rate

- `https://www.bopa.ad/robots.txt`: `User-agent: *` / `Disallow:` (nothing disallowed), no rule for AI crawlers;
- One request at a time, about one a second.

## Legal basis for reuse

1. Official texts are not protected by copyright: Llei sobre drets d'autor i drets veïns, del 10 de juny de 1999 (BOPA
   núm. 38, any 1999, 6 July 1999; in this repository under `{{COPYRIGHT_DIR}}`), article 4(2): "Cap text oficial de
   naturalesa legislativa, administrativa o judicial, com tampoc cap traducció oficial seva, queden protegits per
   aquesta Llei."
2. The BOPA's legal notice (https://www.bopa.ad/AvisLegal, "Condicions generals d'utilització de la informació
   continguda a la seu electrònica del Butlletí Oficial del Principat d'Andorra", read 2026-10-29) allows "la còpia i
   la difusió", "l'adaptació, l'extracció, la reordenació i la combinació" and "la reproducció, la distribució, la
   comunicació pública o la transformació necessària per a aquesta utilització, en qualsevol modalitat i format", on
   conditions: the meaning must not be distorted; nothing may say or suggest that the BOPA Service takes part in,
   sponsors or supports the use; metadata on update dates and conditions of use, where included, must be kept
   unchanged; BOPA domains, logos and graphic elements must not be used. The full text is quoted in `LICENSE`.

## In-force dates

Each law's own provision on its entry into force, counted from its BOPA publication date; failing that, the general
rule of the Codi de l'Administració of 29 March 1989, article 9 (BOPA 1989 núm. 6; in this repository under
`{{CODI_DIR}}`): "Llevat que es disposi altrament per llei dels Coprínceps o del Consell General, les normes jurídiques
entraran en vigor als quinze dies de llur publicació íntegra."
