# KJV and Russian Synodal comparison

Generate a separate KJV dataset from the supplied archive:

```sh
python3 scripts/import_kjv_archive.py /path/to/eng-kjv2006_usfm.zip output/kjv
```

Preserve the ZIP unchanged. The importer only accepts the reviewed SHA-256 checksum recorded in [the KJV source record](01_SOURCES/KJV2006/SOURCE.md). Generated output is not committed and can be recreated. The existing WEB and Russian importers remain available.

With the Russian dataset already generated in `output/russyn`, compare a verified pilot verse:

```sh
python3 scripts/compare_russyn_kjv.py "Римлянам 14:24" --from russyn
python3 scripts/compare_russyn_kjv.py "Psalm 23:1" --from kjv
```

Use `--russyn-data` and `--kjv-data` to change dataset paths. The pilot covers only 13 checked relationships, including Russian Psalm 22:1–6 / KJV Psalm 23:1–6, John 3:16–18, Numbers 13:1 / 12:16, Jonah 2:1 / 1:17, Daniel 3:31 / 4:1, and Romans 14:24 / 16:25. Missing entries are unverified; the tool does not guess. Source archive checksums in generated manifests are checked, but this does not verify that generated JSON was not altered. Source notes are displayed where available. Further mapping must account for psalm headings and partial or merged verses.

Look up or search the KJV dataset using the existing tools with `--data output/kjv`. Run tests with `python3 -m unittest discover -s tests -v`.
