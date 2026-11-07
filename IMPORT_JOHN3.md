# John 3 USFM pilot importer

This pilot imports chapter 3 from the supplied Gospel of John USFM file and writes UTF-8 JSON. It requires Python 3 and no additional packages.

```sh
python3 scripts/import_john3.py /path/to/73-JHNengwebp.usfm output/john3.json
python3 -m unittest discover -s tests -v
```

The file used for the pilot identifies itself as World English Bible, Gospel of John. Its SHA-256 is `a94f67ede545be83cf1fe2f4be3dfc05ed4af64068df469a495394e0fe68913e`. The original archive and its precise source and version have not been verified. The source file is not included in this branch. Retain the original source unchanged and record archive provenance before a full import or redistribution.

Each record contains readable verse text, footnotes, Strong's annotations as encoded in the source, and raw USFM for auditability. The raw USFM retains formatting and note positions. The plain text omits footnotes and formatting. Annotations are source claims attached to English words, not independently verified Greek alignment. No canonical word IDs or versification assumptions are made.

The importer checks that the file identifies John, chapter 3 occurs exactly once, and verses 1–36 are present in order. Unsupported USFM markers cause an error instead of silent data loss. It is designed only for this John 3 pilot; it is not a general USFM parser. Do not manually edit generated JSON. A publisher's World English Bible text is public domain, but assess provenance and rights for all annotations and downloaded materials separately.
