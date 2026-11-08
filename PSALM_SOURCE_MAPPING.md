# Psalm source mapping pipeline

Generate a structurally checked candidate map and a short exception summary from the pinned CrossWire JSword Synodal-to-KJV mapping. These entries are **source-mapped, not individually verified text matches**. The default comparison still uses only the small text-checked pilot; you must explicitly supply the generated candidate map to include the source-mapped entries.

First generate the Russian and KJV datasets (see `RUSSIAN_SYNODAL.md` and `KJV.md`). Then download the pinned mapping and build:

```sh
curl -L https://raw.githubusercontent.com/crosswire/jsword/a2c51f3c3a55416f3c991a67ef3d635c7ee55330/src/main/resources/org/crosswire/jsword/versification/Synodal.properties -o Synodal.properties
python3 scripts/build_psalm_source_map.py --crosswire Synodal.properties
```

This writes `output/psalms_source_map.json` and `output/psalms_source_summary.json`. Use `--russyn-data`, `--kjv-data`, `--output`, and `--summary` for different locations. Each candidate retains the source rule and line. The summary lists excluded categories and unparsed rules. The pinned external source is not included in the repository; its header identifies CrossWire copyright and LGPL-2.1-or-later. Preserve the original notices and assess license obligations before redistributing the source or derivative data.

Compare a source-mapped candidate:

```sh
python3 scripts/compare_russyn_kjv.py "Псалом 3:2" --from russyn --source-map output/psalms_source_map.json
```

The output labels it **source-mapped candidate** and states that text equivalence has not been individually checked. Pilot relationships are preferred and identified separately. Matching references alone are never assumed. The command checks that the candidate map and pilot identify the same source archive checksums and that the pilot has not changed since map generation. Checksums in the manifests do not verify the generated verse files themselves. Regenerate if those files have changed.

## What is included

The pipeline accepts only unambiguous one-source-to-one-target verse rules where both records exist and the target is not shared by another parsed rule. It reserves all text-checked pilot verses for the pilot. It excludes headings, partial-verse notation, multiple targets, overlapping or unparsed rules, missing targets, and unlisted references; the existing audit describes the exact rules and locations for editorial review. A source rule's structural consistency does **not** establish that it applies perfectly to these particular editions.

On the supplied archives it produces 2,337 source-mapped candidates from 2,526 Russian Psalm verse records. Eight Psalm records are covered by the text-checked pilot; 118 heading/part cases, 16 records affected by unparsed rules, and 47 records with no explicit parsed rule remain outside the source-mapped output. These counts reflect source-side records, not total verified correspondences.

## Investigated exceptions

Direct comparison of the archive text confirms Russian Psalm 12:6 spans KJV Psalm 13:5–6; the upstream line has a cross-chapter/reversed end reference and is not parsed automatically. Russian Psalm 89:6 spans KJV Psalm 90:5–6. Those two explicit relationships are added to the text-checked pilot, which is checked first in both directions. Other portions of the Psalm 89 range still require review. Do not substitute a simple offset: the numbering changes around the merged verse.

The current interpreter classifies heading and partial-verse notation for review rather than presenting it as a resolved verse mapping. A future representation needs explicit heading and verse-part references before those cases can be compared accurately. See `PSALM_MAPPING_AUDIT.md` and the source link in each output for the original rules.

Tests: `python3 -m unittest discover -s tests -v`.
