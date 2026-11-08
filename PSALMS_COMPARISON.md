# Russian–KJV Psalms comparison

Generate a reference map using the two previously imported datasets and the pinned CrossWire source file from `PSALM_SOURCE_MAPPING.md`:

```sh
python3 scripts/build_complete_psalm_map.py --crosswire Synodal.properties
```

The default output is `output/psalms_complete_map.json`. Use `--russyn-data`, `--kjv-data`, or `--output` for other locations. The generated file is not committed. The builder checks source and declared archive checksums. Dataset manifest checksums identify the declared archives, not the integrity of generated JSON files.

Once this map exists, the existing command automatically uses it for Psalm references:

```sh
python3 scripts/compare_russyn_kjv.py "Псалом 86:2" --from russyn
python3 scripts/compare_russyn_kjv.py "Psalm 51:0" --from kjv
```

Verse `0` denotes a source heading, not a numbered Scripture verse. A KJV heading may correspond to more than one Russian location. Where CrossWire identifies a heading part, the result shows the full heading as context and makes clear that the exact part is not isolated. The `--psalm-map /path/to/map.json` option selects a different location. The original pilot remains in use when the full map is absent, for non-Psalm references, or when the earlier `--source-map` option is explicitly supplied.

## Coverage and confidence

The builder maps all 2,526 numbered Russian Psalm records and covers all 2,461 numbered KJV Psalm records, plus all 116 KJV Psalm headings. It adds 51 separate Russian-to-KJV preamble-heading relationships. These are record counts for the two specific archives, not a guarantee that every phrase or translation detail has an identical counterpart.

Most correspondences follow the pinned CrossWire source and are **not individually verified against the texts**. Results identify their status and source rule. Carefully checked edition adjustments include Russian Psalm 86:1–2 and Psalm 89, and the 47 equal-reference verses in Russian/KJV Psalms 1, 2 and 148–150. The 15-entry text-checked pilot still takes precedence. For example, Russian Psalm 86:2 combines KJV Psalm 87:1–2; Russian Psalm 89:6 combines KJV Psalm 90:5–6. In other cases the comparison may show a complete verse even if the relationship involves only part of its text.

The Russian source also has 29 preamble headings for which a direct counterpart has not been established. They are recorded in `unresolved_russian_headings`; querying one with `:0` displays the source heading and explicitly reports the missing established counterpart. Some may correspond to part of a KJV verse; no equivalence is invented. The eight CrossWire heading-part relationships show the full heading, not a falsely precise substring.

The CrossWire mapping is retrieved from JSword revision `a2c51f3c3a55416f3c991a67ef3d635c7ee55330` and checked by SHA-256. Its header identifies LGPL-2.1-or-later and credits CrossWire contributors. It is not bundled; preserve its notices and assess license obligations before redistributing the original file or derived data. Source-mapped records preserve the applicable rule and line; project-specific overrides describe their evidence. The builder reports unexpected structural gaps or missing locations instead of silently guessing.

Run tests with `python3 -m unittest discover -s tests -v`.
