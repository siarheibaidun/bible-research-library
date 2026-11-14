# Original-language and Dutch Bible index

Build a supplementary, searchable SQLite snapshot for the Hebrew/Aramaic Westminster Leningrad Codex (WLC), unfoldingWord Greek New Testament v0.34 (UGNT), and Dutch De Heilige Schrift 1917. The 1917 Dutch text is not HSV or NBV21. The snapshot includes raw USFM per verse, source-specific word attributes (Strong numbers, morphology, and Greek lemmas where supplied), footnotes, source digests, license notices and KJV reference candidates. It does not replace the existing Russian–KJV index.

## Sources and reproducible build

Download the reviewed source archives:

* WLC: https://ebible.org/Scriptures/hboWLC_usfm.zip (reviewed SHA-256 `464225e119973cb7e12a30777c2d5e7f543f083529b00b909d620c617dbd1df7`). WLC text is public domain; morphology and lemma data are CC BY-SA 3.0; attribute the Open Scriptures Hebrew Bible Project.
* UGNT v0.34: https://git.door43.org/unfoldingWord/el-x-koine_ugnt/archive/v0.34.zip (SHA-256 `07318be27d0027146a62363c20ffedd0db695d7680f4b32c8ae8bd3020a29d00`), CC BY-SA 4.0. Attribute unfoldingWord and preserve its license and trademark terms.
* De Heilige Schrift 1917: https://ebible.org/Scriptures/nld_usfm.zip (reviewed SHA-256 `7c76b55b640789304a7ff0a505236f69e715fa7fca4ebcf8dd237ee6c16cf58c`); its source declares Public Domain.
* Hebrew/KJV versification rules: https://raw.githubusercontent.com/crosswire/jsword/a2c51f3c3a55416f3c991a67ef3d635c7ee55330/src/main/resources/org/crosswire/jsword/versification/Leningrad.properties (SHA-256 `9ae15279ce7456666ad5c5af1215e2b767028215ed30853914d029403b24424b`), CrossWire JSword, LGPL-2.1-or-later. Retain its notices and assess the applicable requirements when distributing derived data.

Archive hashes are recorded in the output; check the above reviewed hashes before rebuilding. eBible archives may change. The builder validates book coverage, duplicate references, UTF-8 and known markup, rejects unsupported markup, and records unsupported mapping rules as unresolved. The KJV index must be the existing Bible Research Search snapshot, whose KJV source hash is checked. The output must not already exist.

```sh
python3 scripts/build_original_index.py \
  --he /path/to/hboWLC_usfm.zip --greek /path/to/ugnt-v0.34.zip \
  --dutch /path/to/nld_usfm.zip --rules /path/to/Leningrad.properties \
  --kjv-index /path/to/bible-research-search.sqlite3 \
  --output output/originals_dutch.sqlite3
```

## Lookup

```sh
python3 scripts/original_search.py --database output/originals_dutch.sqlite3 verse --source hboWLC --book GEN --chapter 1 --verse 1 --tokens
python3 scripts/original_search.py --database output/originals_dutch.sqlite3 search --source ugnt 'λογος' --limit 20
python3 scripts/original_search.py --database output/originals_dutch.sqlite3 cross --bible-database /path/to/bible-research-search.sqlite3 --from-translation russyn --book PSA --chapter 22 --verse 1
```

Text search is literal case- and diacritic-insensitive substring search, not semantic or lemma search. Word annotations can be retrieved, not used as a dedicated lemma index. `cross` bridges through the existing Russian/KJV mapping, retains both statuses, and returns candidates: this is not word alignment or proof of identical scope. WLC rules come from CrossWire, while unlisted WLC locations and Greek/Dutch locations use unverified same-reference candidates. Part and heading rules may return full verses. Records without established counterparts are explicitly unresolved; the reviewed UGNT has no current KJV links for 3 John 1:15 and Revelation 12:18. Existing Russian mappings also include unverified candidates and source-specific adjustments. Do not claim full correspondence or exhaustiveness.

Default tests: `python3 -m unittest discover -s tests -p 'test_original_index.py' -v`. Set `ORIGINAL_TEST_DB` and `BIBLE_TEST_DB` to run integration checks as well.
