# Source record: World English Bible (engwebp)

## Identification

- **Resource:** World English Bible, updated 66-book edition, English, USFM archive.
- **Archive provided for the project:** `engwebp_usfm.zip`
- **Archive SHA-256:** `a93df5571009fed56f77e3ac1d3ce71c9a3a3df1486f7570cc7a8f823192fdba`
- **Archive size:** 2,908,558 bytes.
- **Edition:** the archive's `copr.htm` identifies the text as the 2020 stable text edition.
- **Archive copyright page generation:** 30 October 2026, from source files dated 30 October 2026, according to that page. This is not a verified download date.
- **Publisher page:** https://ebible.org/details.php?id=engwebp
- **Exact URL and download date for this specific archive:** not verified. The publisher page is a reference, not proof of the original download location.
- **Scope:** 66 book USFM files plus front matter, glossary, copyright page and other supporting files; 72 archive entries in total.

## Rights and attribution

The archive's `copr.htm` says the World English Bible text is public domain and identifies “World English Bible” as a trademark of eBible.org. It asks that changed text not be called the World English Bible. Keep the source notice and attribution with any distribution. The provenance and rights of the Strong's annotations and any other supplementary material have not been independently verified; review those separately before redistributing them.

## Preservation and reproducibility

Keep the original ZIP unchanged in durable storage. It is not committed to this repository. Verify its SHA-256 against this record before importing. Store derived JSON separately from the original source and regenerate it using the project's importer; the generated manifest records the checksum and per-book source hashes. The importer retains much original USFM but does not provide a lossless round trip; the ZIP remains authoritative.

```sh
python3 scripts/import_web_archive.py /path/to/engwebp_usfm.zip output/web
```

See [IMPORT_WEB.md](../../IMPORT_WEB.md) and [PASSAGE_SEARCH.md](../../PASSAGE_SEARCH.md) for instructions and limitations. The permanent storage location, exact archive acquisition details, versification mapping, and redistribution terms for annotations remain to be confirmed.
