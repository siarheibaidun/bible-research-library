# Passage lookup and keyword search

The commands use the generated World English Bible dataset. If you have not generated it yet, run from the repository root:

```sh
python3 scripts/import_web_archive.py /path/to/engwebp_usfm.zip output/web
```

Show a chapter, one verse, or an inclusive range within one chapter:

```sh
python3 scripts/lookup_passage.py "John 3"
python3 scripts/lookup_passage.py "John 3:16-18"
python3 scripts/lookup_passage.py "1 John 4:8"
```

Passages show notes and source details. Cross-chapter ranges are not supported. Full English book names and USFM book codes are supported.

Search verse text for a literal word or phrase, ignoring capitalization:

```sh
python3 scripts/search_verses.py "God is love"
python3 scripts/search_verses.py "love" --book "1 John" --limit 10
```

Search matches substrings, so `love` also matches `loved`; it does not search notes or perform word stemming or semantic search. Results follow book and verse order. The default maximum is 20 displayed results; the total count includes all matches. Specify another generated dataset directory with `--data /path/to/dataset`. The ZIP and generated data are not stored in the repository; see [IMPORT_WEB.md](IMPORT_WEB.md) for source information.

Run checks with:

```sh
python3 -m unittest discover -s tests -v
```
