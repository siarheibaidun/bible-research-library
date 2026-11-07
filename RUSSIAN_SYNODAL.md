# Russian Synodal Bible

Import the supplied `russyn_usfm.zip` independently from the English dataset:

```sh
python3 scripts/import_russyn_archive.py /path/to/russyn_usfm.zip output/russyn
python3 scripts/lookup_verse.py "Иоанна 3:16" --data output/russyn
python3 scripts/lookup_passage.py "Иоанна 3:16-18" --data output/russyn
python3 scripts/search_verses.py "Бог есть любовь" --data output/russyn
```

English book names and USFM book codes remain available. Common Russian names are supported; `1 Царств` through `4 Царств` correspond to USFM `1SA`, `2SA`, `1KI`, and `2KI`. Russian names are displayed for this dataset. Search is a case-insensitive literal substring search. See `PASSAGE_SEARCH.md` for options.

The importer's accepted archive has SHA-256 `9af20fe73fff9370acc8fd03cc0ffa718e1cf107d83fc401d41dcadc6c4e4a88`. Other archive versions are rejected until reviewed and documented. The ZIP is not committed; preserve it unchanged in durable storage. Generated JSON is derived data and can be recreated.

The two datasets keep their own references. They are **not** automatically aligned: for instance, Russian Psalm 22:1 and WEB Psalm 23:1 both begin with the Lord as shepherd. Do not infer cross-translation equivalence from matching references. The underlying versification systems and mappings require further research and validation.

Run the tests using `python3 -m unittest discover -s tests -v`.
