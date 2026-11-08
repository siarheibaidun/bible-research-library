# Russian–KJV Bible comparison

Generate the mapping for the 65 books outside Psalms using the same pinned CrossWire file and the two datasets already used for Psalms:

```sh
python3 scripts/build_bible_source_map.py --crosswire Synodal.properties
```

The default output is `output/bible_other_books_map.json`. If `Synodal.properties` is not present, see [PSALM_SOURCE_MAPPING.md](PSALM_SOURCE_MAPPING.md) for the pinned download link. `--russyn-data`, `--kjv-data` and `--output` select other paths. The generated map is reproducible and is not committed. The pinned mapping is supplied separately; its header identifies CrossWire copyright and LGPL-2.1-or-later. Preserve its notices and assess license requirements before distributing the original file or derived mapping data.

The existing command will automatically use the generated map for non-Psalm books and the full Psalm map for Psalms if each file exists in its default location:

```sh
python3 scripts/compare_russyn_kjv.py "Притчи 13:15" --from russyn
python3 scripts/compare_russyn_kjv.py "1 Kings 18:33" --from kjv
```

The first example compares Russian Proverbs 13:15 with KJV Proverbs 13:14. You can select a non-default map with `--bible-map`; use `--psalm-map` for a Psalm map. If maps are absent, the earlier limited pilot is used instead. Results show evidence, status, and source archive checksums. Where a mapping refers to a part of a verse, the whole verse is shown as context with an explicit limitation.

## Coverage and limitations

For the exact source archives, all **28,643 Russian numbered records outside Psalms** are accounted for: 28,637 have at least one KJV target and six are marked `no_numbered_counterpart`. The six are Joshua 24:34–36, Proverbs 4:28–29, and Proverbs 13:14 in the Russian source. This means no direct numbered counterpart has been established in the corresponding KJV book; it does not make a claim about related material elsewhere. One KJV record, Song of Solomon 1:1, has no directly established numbered Russian counterpart and is displayed as unresolved rather than guessed.

The map draws on CrossWire's Synodal-to-KJV rules for explicit shifts, **assumes equal references where no explicit rule applies**, and makes edition-specific adjustments checked against the two source texts. Most published-rule and equal-reference matches have not been individually text-verified; an equal reference is a candidate, not proof of identical scope or meaning. Actual source editions may contain additional material inside a verse, and future examination may identify further exceptions. Results label their status.

Among the checked adjustments are Russian Proverbs 13:15–26 / KJV 13:14–25 after a Russian-only verse; Russian Acts 19:40 / KJV 19:40–41; Russian 3 John 1:14–15 / portions of KJV 1:14; Russian Leviticus 14:55–56 / KJV 14:55–57; and Russian 2 Corinthians 11:32 / KJV 11:32–33. The importer handles published cross-chapter and verse-part rules; it rejects unsupported rules, unexpected overlaps and mismatching source checksums rather than silently falling back.

The source archives and dataset manifests are pinned by checksum; the manifest checksum does not independently verify that generated verse files have not been edited. A generated map is also tied to the current text-checked pilot; regenerate if that pilot changes. The KJV and Russian dataset archives and the original LGPL mapping are not bundled.

Psalms have their own source-specific mapping. See [PSALMS_COMPARISON.md](PSALMS_COMPARISON.md), including the 29 Russian preamble headings without an established direct KJV counterpart. Run tests with `python3 -m unittest discover -s tests -v`.
