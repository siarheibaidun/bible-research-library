# Matthew Henry commentary importer

This imports the reviewed SWORD MHC zCom4, OSIS, BOOK-compressed, KJV-versification archive into a local SQLite database, using only Python's standard library. The original OSIS fragment, normalized plain text, SWORD index coordinates, internal cross-references, and KJV verse links are preserved. Identical linked fragments are stored once. Database text is English. A SQLite FTS5 index is included for lexical searches; this is not semantic search or an automatic ChatGPT integration.

## Prerequisites

Generate the KJV JSON dataset according to [KJV.md](KJV.md). For Russian references, generate **both** the Psalms and other-books maps according to [PSALMS_COMPARISON.md](PSALMS_COMPARISON.md) and [BIBLE_COMPARISON.md](BIBLE_COMPARISON.md). They require the Russian and KJV datasets and the pinned `Synodal.properties` file. The source archives, generated datasets, mapping files and output database are not committed.

## Build and use

From the repository root, with the default generated paths:

```sh
python3 scripts/import_mhc.py \
  --archive /path/to/MHC.zip \
  --kjv-dir output/kjv \
  --mapping output/psalms_complete_map.json \
  --mapping output/bible_other_books_map.json \
  --output output/matthew_henry_commentary.sqlite3
```

The destination must not already exist. The maps are optional for KJV lookups but both are needed for Russian coverage. The importer checks archive format, block sizes, index bounds, the complete KJV verse count, and that each mapping's declared KJV archive checksum matches the generated dataset manifest. The manifest checksum identifies the source archive; it does not independently verify the generated JSON contents. Source archive SHA-256 and each map SHA-256 are retained in metadata.

Look up Russian Psalm 22:1 or KJV John 3:16 (USFM book codes):

```sh
python3 scripts/lookup_mhc.py --db output/matthew_henry_commentary.sqlite3 --translation russyn --book PSA --chapter 22 --verse 1
python3 scripts/lookup_mhc.py --db output/matthew_henry_commentary.sqlite3 --translation kjv --book JHN --chapter 3 --verse 16
```

Results contain the complete matching fragment, KJV verses sharing it, internal OSIS references and mapping status/evidence. A Russian mapping with no target returns no commentary rather than assuming identical verse numbers. Some mappings concern only part of a verse; the full commentary fragment is returned with the stored part labels. Cross-references are the author's references within a fragment, not necessarily its subject. The existing maps describe candidates and often have not been individually text-checked; their original limitations still apply. Verse-zero Psalm headings are excluded from this first version. OSIS structural introductions that are not associated with a numbered verse are not imported independently.

On the reviewed archive the four verses JOS 18:1, 1SA 25:1, 2SA 22:1 and PRO 11:20 have zero-length index entries and produce no result; no adjacent commentary is inferred. The archive's configuration declares module MHC version 2.2 and Public Domain; retain source attribution and verify applicable redistribution terms before distributing source-derived material. The archive SHA-256 is `6bcb936873ca144e317805e5c1677940fd86e2403f7c14517752e44f25c8882b`.

Run unit tests with `python3 -m unittest discover -s tests -p 'test_mhc.py' -v`; add `MHC_TEST_DB=output/matthew_henry_commentary.sqlite3` to also run integration tests against the actual module.
