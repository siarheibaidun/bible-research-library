---
name: bible-research-search
description: Search the Bible Research Library's complete Russian Synodal and King James Bible text in ChatGPT, locate verses by phrase or topic, retrieve passages, and compare verse references using the project's source-attributed Russian–KJV mappings. Use for Bible verse searches, references, concordance-style lookups, or cross-translation comparison, including Russian and English requests. Find and explain Matthew Henry's commentary on Bible verses or topics using the user's indexed English commentary, with Russian–KJV reference mapping.
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

## Open-ended Russian question search

For an open-ended question seeking Bible passages, locate the Library file `russian_bible_passages.sqlite3` by name and materialize it using the Library skill. It is a fixed snapshot of the Synodal text.

Analyze the question and generate distinct Russian stems or terms representing its concepts and likely biblical wording, including synonyms. Run:

```bash
python3 "$SKILL_DIR/scripts/question_search.py" --database "$PASSAGE_DB" --term детей --term отц --term матер --term воспиты --term настав --limit 50
```

Replace the terms with terms relevant to the current question. Repeat with other concept groups for broad questions. The script retrieves overlapping passages by literal word prefixes and combines rankings; this is AI-assisted query expansion and lexical retrieval, **not an embedding model or semantic-vector index**. Inspect candidates, merge overlaps, and retrieve exact verses and context from `search.py` before answering. Cite sources and distinguish direct from indirect relevance. The approach can miss relevant texts; never claim exhaustive results.

## Experimental parent–child topic

For a request about relationships between parents and children, use the experimental thematic prototype before supplementing it with literal searches. Run:

```bash
python3 "$SKILL_DIR/scripts/topic_search.py" --database "$BIBLE_DB" --translation russyn
```

Use `--translation kjv` for KJV. The result is a curated list of 15 passages grouped by category and fetched from the source text; it is not an exhaustive list or embedding-based semantic search. Use `--candidates` to request additional literal keyword matches for assessment, but never assert that unreviewed lexical candidates are relevant. Inspect surrounding context as necessary and explain indirect parallels, such as a parable or theological analogy. If the user asks for all passages, explicitly acknowledge incompleteness and combine this seed list with additional searches; do not claim completeness.

## Matthew Henry commentary

For requests for Matthew Henry's interpretation or searches within his commentary, use the user's Library file named `matthew_henry_commentary.sqlite3`. Locate and materialize the intended latest file via the Library skill, following its transfer and metadata workflow. Do not hard-code or publish private Library file identifiers. Reuse a suitable local copy only if verified in the current session. If inaccessible, state that you could not consult the user's commentary dataset; do not pretend another source or memory is this dataset.

Run the bundled script with Python 3 and the materialized database path. Convert a requested Bible book to its USFM code (e.g. `PSA`, `JHN`, `GEN`, `1SA`). Use the reference and translation the user actually gave; default to Russian Synodal for Russian-language verse requests. For a range, query each verse, deduplicate commentary fragment IDs, and do not assume a fragment only covers the requested verse.

```bash
python3 "$SKILL_DIR/scripts/commentary_search.py" --database "$MHC_DB" verse --translation russyn --book PSA --chapter 22 --verse 1
python3 "$SKILL_DIR/scripts/commentary_search.py" --database "$MHC_DB" verse --translation kjv --book JHN --chapter 3 --verse 16
python3 "$SKILL_DIR/scripts/commentary_search.py" --database "$MHC_DB" search 'shepherd' --limit 10
```

The commentary is English. Explain it in the user's language or translate relevant portions as requested, distinguishing translation or summary from quotation. Cite Matthew Henry, the KJV passage covered by each fragment, and the requested Russian reference when applicable. For Russian references, use only the database's explicit mapping; show differing KJV references and mention uncertain, partial, or assumed matches. Missing mapping, headings and entries have no automatically inferred commentary. The four KJV verses JOS 18:1, 1SA 25:1, 2SA 22:1 and PRO 11:20 have empty index entries. A fragment can cover multiple verses; internal cross-references are not the fragment's own coverage.

A `verse` result defaults to the first 12,000 characters of a potentially long fragment; inspect `truncated` and increase `--max-chars` (up to 2,000,000) before claiming a full reading. For topical requests, translate concepts into multiple appropriate **English** search terms and use `search` for lexical FTS5 phrase matches. Results contain snippets and KJV verse links; inspect full matching commentary with `verse` before drawing conclusions. The search is not semantic and is not exhaustive. Never claim the commentary dataset contains Bible translations other than the author's embedded KJV excerpts, or that the comments are the biblical text itself. The source declares Public Domain and identifies MHC version 2.2.

## Mapping safety

Display the source reference and mapped target reference separately. The snapshot includes source-mapped relationships, edition-specific overrides, and assumed equal references; most have not been individually checked against both texts. Report the mapping status and qualify uncertain or implicit matches, especially when explaining differences. Multiple relationships may match a KJV verse. A mapped part (`part`) or heading can return the full verse or heading as context; never present that larger text as an exact isolated span. If a relation has no target, is absent or has `counterpart_unresolved`, explicitly report no established counterpart instead of guessing. Psalm heading numbering differs between translations.

When seeking later editions or additional translations, first verify whether an updated index exists; the user's repository is `siarheibaidun/bible-research-library`. Do not silently replace the snapshot, relicense third-party mapping data, or claim changes were incorporated without rebuilding and checking the index.
