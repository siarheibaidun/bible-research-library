---
name: bible-research-search
description: Search the Bible Research Library's complete Russian Synodal and King James Bible text in ChatGPT, locate verses by phrase or topic, retrieve passages, and compare verse references using the project's source-attributed Russian–KJV mappings. Use for Bible verse searches, references, concordance-style lookups, or cross-translation comparison, including Russian and English requests.
---

# Bible Research Search

Use the indexed Bible Research Library snapshot to answer from actual source texts rather than memory. The index contains the user's Russian Synodal (`russyn`) and KJV (`kjv`) editions and their Psalms and whole-Bible reference mappings. It is a snapshot, not a live index: do not claim later repository changes are included. The source/mapping metadata in script output describes the underlying editions and checksums.

## Obtain the database

Find the ChatGPT Library file named `bible-research-search.sqlite3` using the Library skill. Identify the user’s intended file and use the Library skill’s materialization workflow to bring the latest version into the current workspace. Do not hard-code or publish private Library file identifiers. Do not use a stale scratch path. If a suitable local copy is already present and verified for this session, reuse it. If Library is inaccessible, report that the index cannot be reached; do not pretend a web search or model memory is a search of the user's index.

## Search and retrieve

Run the bundled `scripts/search.py` with Python 3 and the materialized database path. Resolve the skill directory from the environment providing this skill; do not assume the paths from an earlier conversation.

```bash
python3 "$SKILL_DIR/scripts/search.py" --database "$BIBLE_DB" search 'Бог есть любовь' --translation russyn
python3 "$SKILL_DIR/scripts/search.py" --database "$BIBLE_DB" search 'love' --translation kjv --book '1 John' --limit 20
python3 "$SKILL_DIR/scripts/search.py" --database "$BIBLE_DB" verse 'Псалом 86:2' --translation russyn --parallel
```

`search` searches numbered verses across every book by case-insensitive literal substring; it does not search notes, stem words, handle spelling variants, or perform semantic search. It returns the total and paginated results; use `--offset` and `--limit` (maximum 100) to retrieve additional results. Scope `--book` accepts English or supported Russian names. `verse` retrieves one reference and `--parallel` returns the mapping relationships and source notes. For a passage, retrieve each requested verse in order; do not invent unreturned text. Psalm heading references use verse `0` and are not numbered Scripture verses. No other translation is indexed.

For a topical request, choose and search multiple relevant literal word forms, synonyms, and languages when useful. Apply contextual judgment to the actual returned text. Clearly distinguish a selected set of relevant passages from an exhaustive word search; do not assert exhaustive conceptual coverage. For an exact phrase, report the search's translation, literal matching, total and any truncation. If spelling, punctuation or inflection may affect the answer, say so and perform sensible alternate searches.

When the user does not specify a translation, use the language of their request as the default: Russian Synodal for Russian requests, KJV for English. Search both if comparison is requested. Cite book, chapter, verse and translation for each result. Preserve wording, note-only verses, footnotes, and textual differences; never supply a made-up quote.

## Mapping safety

Display the source reference and mapped target reference separately. The snapshot includes source-mapped relationships, edition-specific overrides, and assumed equal references; most have not been individually checked against both texts. Report the mapping status and qualify uncertain or implicit matches, especially when explaining differences. Multiple relationships may match a KJV verse. A mapped part (`part`) or heading can return the full verse or heading as context; never present that larger text as an exact isolated span. If a relation has no target, is absent or has `counterpart_unresolved`, explicitly report no established counterpart instead of guessing. Psalm heading numbering differs between translations.

When seeking later editions or additional translations, first verify whether an updated index exists; the user's repository is `siarheibaidun/bible-research-library`. Do not silently replace the snapshot, relicense third-party mapping data, or claim changes were incorporated without rebuilding and checking the index.
