# Russian–KJV Psalm mapping audit

This produces a **review-only candidate report** from CrossWire's Synodal-to-KJV mapping and the exact editions of the Russian Synodal and KJV datasets used by this project. It does not add mappings to `compare_russyn_kjv.py` and does not automatically verify equivalence between texts. The two generated datasets must already exist (see `RUSSIAN_SYNODAL.md` and `KJV.md`).

Download the external mapping at the pinned revision:

```sh
curl -L https://raw.githubusercontent.com/crosswire/jsword/a2c51f3c3a55416f3c991a67ef3d635c7ee55330/src/main/resources/org/crosswire/jsword/versification/Synodal.properties -o Synodal.properties
python3 scripts/audit_psalm_mapping.py --crosswire Synodal.properties
```

The audit expects `output/russyn` and `output/kjv`, and writes `output/psalm_mapping_review.json`; use `--russyn-data`, `--kjv-data`, and `--output` to change these paths. It checks the source file and declared dataset archive hashes. Dataset manifest checksums do not independently verify the generated JSON's integrity; regenerate data from the original archives to restore it.

The report contains Russian verse text, candidate source rules, proposed KJV verses or raw heading markup, line references, and explicit review categories. It does not assume same-number matches where no rule exists. Reverse coverage counts show KJV verses with at least one parsed candidate; they do not establish equivalence. Rules that cannot be parsed are listed, and their affected source verses are flagged where their source expression can be enumerated.

| Status | Meaning |
| --- | --- |
| `candidate_text_review` | One source and one target verse exist; their relationship still requires text review. |
| `heading_or_part_review` | A target uses heading/verse-zero notation or an explicit verse part. |
| `multiple_targets_review` | A source has multiple non-heading targets requiring boundary review. |
| `target_missing_review` | A candidate target verse is not present in this dataset. |
| `overlapping_rules_review` | More than one parsed rule describes the source reference. |
| `unparsed_rule_review` | A rule affecting this source could not be interpreted safely. |
| `no_explicit_rule` | No parsed or enumerated unparsed rule covers the source; no identity assumption is made. |

The upstream file is `Synodal.properties` at CrossWire JSword revision `a2c51f3c3a55416f3c991a67ef3d635c7ee55330`, SHA-256 `76385bbd47834482c651e509e898d704cf27b5d4037ecff26ec7baf45f1edba6`. Its header identifies CrossWire copyright and LGPL-2.1-or-later. The original mapping file is not bundled in this repository. Preserve its notices and assess license requirements if distributing the file or a derived report. See [CrossWire's mapping syntax](https://ftp.crosswire.org/jsword/javadoc/org/crosswire/jsword/versification/VersificationToKJVMapper.html). The referenced scheme is Synodal-to-KJV, but its applicability to each passage in these exact editions has not been established.

On the two supplied datasets the first run reported 2,342 one-to-one candidates for text review, 119 heading/part cases, 18 verses affected by two unparsed rules, and 47 source verses with no explicit parsed rule. Those counts are review categories, not verified alignments. The two unparsed rules require special attention: a cross-chapter/reversed target and unequal range lengths. The latter may have a special meaning in JSword; it is intentionally not guessed here. Psalm 22:1 illustrates another key difference: the upstream mapping includes both a heading and a verse, while our Russian source keeps its heading in a chapter preamble.

Run checks with `python3 -m unittest discover -s tests -v`.
