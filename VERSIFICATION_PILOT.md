# Russian Synodal–WEB versification pilot

The pilot records nine explicit correspondences between the two specific source archives: Russian Psalm 22:1–6 ↔ WEB Psalm 23:1–6, and John 3:16–18 in each source. The verse texts in those exact archives were compared to establish the pilot correspondences. The mapping describes corresponding portions, not identical wording or identical textual traditions.

The mapping is deliberately incomplete. A missing entry means **not yet verified**, not that no equivalent exists. It makes no automatic equal-reference assumption. It is a project pilot rather than a complete independently reviewed versification scheme. Verse boundaries can differ and later relationships may be one-to-many or many-to-many; lists of references are used to accommodate this. The command currently looks up an individual mapped verse only.

Both datasets must already be generated, as described in `IMPORT_WEB.md` and `RUSSIAN_SYNODAL.md`:

```sh
python3 scripts/compare_translations.py "Псалом 22:1" --from russyn
python3 scripts/compare_translations.py "Psalm 23:1" --from web
python3 scripts/compare_translations.py "John 3:16" --from web
```

Use `--russyn-data` and `--web-data` for other dataset locations. The command checks archive checksums in each generated manifest and reports missing or ambiguous mappings instead of guessing. The checksums identify the archives, not the integrity of each generated JSON file; regenerate from the source to restore derived data. Notes are shown with each mapped verse where present.

## Research and next validation

CrossWire's [versification identification guide](https://wiki.crosswire.org/Alternate_Versification/System_Identification) documents the need for distinct versification systems, including Synodal. Its [JSword mapper documentation](https://ftp.crosswire.org/jsword/javadoc/org/crosswire/jsword/versification/VersificationsMapper.html) describes many-to-many mappings and the use of KJV as an intermediary. The [Copenhagen Alliance versification specification](https://github.com/Copenhagen-Alliance/versification-specification) also describes source-to-base mapping. These are research references, not the source of the nine pilot entries; no external mapping data was copied.

Before extending coverage, identify the versification of these exact editions, assess a suitable authoritative mapping and its license, then test exceptions including headings, omitted verses and split/merged passages against the actual source texts. Record provenance, verification status, and source versions for every mapping; do not fill gaps with automatic same-number matches.

Run tests with `python3 -m unittest discover -s tests -v`.
