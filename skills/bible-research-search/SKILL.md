---
name: bible-research-search
description: Use multilingual vector and lexical search to answer Bible questions in Russian, English or Dutch; retrieve and compare Russian Synodal, KJV, Dutch 1917, Hebrew/Aramaic WLC and Greek UGNT using source-attributed verse mappings and morphology. Find and explain Matthew Henry commentary.
---

# Bible Research Search

Use the indexed Bible Research Library snapshot to answer from actual source texts rather than memory. The unified index contains Russian Synodal, KJV, Dutch 1917, Hebrew/Aramaic WLC and Greek UGNT, source metadata, morphology and reference mappings. It also contains a multilingual vector index over all five editions, with Russian, English and Dutch lexical passage indexes. It is a snapshot, not a live index: do not claim later repository changes are included. The source/mapping metadata in script output describes the underlying editions and checksums.

## Obtain the database

Find the ChatGPT Library file named `bible-research-search.sqlite3` using the Library skill. Identify the user’s intended file and use the Library skill’s materialization workflow to bring the latest version into the current workspace. Do not hard-code or publish private Library file identifiers. Do not use a stale scratch path. If a suitable local copy is already present and verified for this session, reuse it. If Library is inaccessible, report that the index cannot be reached; do not pretend a web search or model memory is a search of the user's index.

## Search and retrieve

Run the bundled `scripts/search.py` with Python 3 and the materialized database path. Resolve the skill directory from the environment providing this skill; do not assume the paths from an earlier conversation.

```bash
python3 "$SKILL_DIR/scripts/search.py" --database "$BIBLE_DB" search 'Бог есть любовь' --translation russyn
python3 "$SKILL_DIR/scripts/search.py" --database "$BIBLE_DB" search 'love' --translation kjv --book '1 John' --limit 20
python3 "$SKILL_DIR/scripts/search.py" --database "$BIBLE_DB" verse 'Псалом 86:2' --translation russyn --parallel
```

`search` searches numbered verses across every book by case-insensitive literal substring; it does not search notes, stem words, handle spelling variants, or perform semantic search. It returns the total and paginated results; use `--offset` and `--limit` (maximum 100) to retrieve additional results. Scope `--book` accepts English or supported Russian names. `verse` retrieves one reference and `--parallel` returns the mapping relationships and source notes. For a passage, retrieve each requested verse in order; do not invent unreturned text. Psalm heading references use verse `0` and are not numbered Scripture verses. This legacy command searches Russian and KJV; use the unified command below for the other editions.

For a topical request, choose and search multiple relevant literal word forms, synonyms, and languages when useful. Apply contextual judgment to the actual returned text. Clearly distinguish a selected set of relevant passages from an exhaustive word search; do not assert exhaustive conceptual coverage. For an exact phrase, report the search's translation, literal matching, total and any truncation. If spelling, punctuation or inflection may affect the answer, say so and perform sensible alternate searches.

When the user does not specify a translation, use the language of their request as the default: Russian Synodal for Russian requests, KJV for English. Search both if comparison is requested. Cite book, chapter, verse and translation for each result. Preserve wording, note-only verses, footnotes, and textual differences; never supply a made-up quote.

## Multilingual semantic search

For open-ended questions or finding Bible passages by meaning, use the vector index in `$BIBLE_DB` first; this is an actual multilingual E5 dense-vector index over overlapping passage windows from all indexed books in all five editions. The model and runtime wheels are stored in the same database. Run:

```bash
python3 "$SKILL_DIR/scripts/semantic_search.py" --database "$BIBLE_DB" 'Как родителям воспитывать детей?' --translation russyn --ru-term родител --ru-term детей --limit 50
python3 "$SKILL_DIR/scripts/semantic_search.py" --database "$BIBLE_DB" 'How should parents care for their children?' --translation nld1917 --limit 50
python3 "$SKILL_DIR/scripts/semantic_search.py" --database "$BIBLE_DB" 'Hoe vind je troost in verdriet?' --translation kjv --limit 50
```

Supply the user's question in its original language; the multilingual model embeds it directly, including when the selected text is in a different language. Choose the edition(s) requested; absent a preference use Russian Synodal for Russian, KJV for English and Dutch 1917 for Dutch. For a comparison across multiple editions, search each edition separately, then use `unified_search.py compare` to map references and inspect their scope. Optional individual `--ru-term`, `--en-term`, `--nl-term` prefixes add lexical rank fusion; choose synonyms in the language of the selected text. Without these options retrieval is vector-only. Exact wording, quotations and exhaustive literal counts still require `unified_search.py search` or `search.py`.

Inspect returned passages and surrounding verses before answering, deduplicate overlaps, cite edition and references, distinguish direct references from analogies, and never claim semantic results are exhaustive. Similarity is not proof of relevance. The Hebrew and Greek original-language vectors use unaccented input while stored text remains unchanged; retrieval quality for Biblical Hebrew, Aramaic and Koine Greek has not been independently established. A long question can be truncated (`query_truncated`); shorten and repeat if true. Source mappings, part/heading caveats and edition differences still apply.

The bundled offline runtime requires Python 3.12 on Linux x86-64 with AVX-512 VNNI; first use extracts verified assets and installs bundled wheels to a temporary cache without network. If unavailable or any model/index check fails, say vector search could not be run; fall back to lexical search only if useful and clearly label it. Never claim an embedding search was performed when it was not.

## Unified search and comparisons

Use the one materialized `$BIBLE_DB` for all Bible texts, mappings, morphology and passage indexes. Identify the user's reference language and source translation. Russian defaults to Synodal, English to KJV, Dutch to Dutch 1917; ask only if the reference is ambiguous. The Dutch source is an old 1917 text, not HSV or NBV21. Convert book names from Russian, English or Dutch, or use USFM book codes.

```bash
python3 "$SKILL_DIR/scripts/unified_search.py" --database "$BIBLE_DB" compare --from russyn --book Псалом --chapter 22 --verse 1 --to nld1917 --to hboWLC
python3 "$SKILL_DIR/scripts/unified_search.py" --database "$BIBLE_DB" compare --from ugnt --book Johannes --chapter 1 --verse 1 --to russyn --to kjv --to nld1917 --tokens
python3 "$SKILL_DIR/scripts/unified_search.py" --database "$BIBLE_DB" search --translation nld1917 'liefde' --limit 20
python3 "$SKILL_DIR/scripts/unified_search.py" --database "$BIBLE_DB" topic --ru-term любов --en-term love --nl-term liefde --limit 50
```

`compare` navigates **from any included edition to any other** through explicit KJV anchors. Show source and mapped references, inspect all paths, and preserve mapping status, KJV parts and evidence. A different canon, an unrepresented book, or an unresolved reference yields no result; never fill it from memory or guess the same number. WLC published-rule links and equal-reference links are candidates, not universal verse equivalences. Parts and headings can return a full verse for context, and compositions may over-include material; no word-level alignment is implied. For 3 John 1:14 the script filters disjoint checked opening/closing parts. UGNT Revelation 12:18 ↔ KJV 13:1 opening is partial and has a textual variant (he stood vs I stood). In a range, query each verse and deduplicate. `--tokens` supplies Strong identifiers, morphology and Greek lemmas as provided by the source; do not equate a Strong number with a proven meaning.

`search` is literal substring matching within one selected edition; spelling and inflection matter, and Hebrew/Greek/Dutch searches ignore diacritics. For lexical supplementation or if vector search is unavailable, analyze a topical question in its context, formulate relevant stems and synonyms, and if looking across languages translate the concepts into all three languages. Pass these yourself via repeated `--ru-term`, `--en-term`, `--nl-term`; the script does not translate queries. `topic` uses lexical prefix retrieval over overlapping passages and rank fusion, not embeddings or semantic search. It may miss relevant verses or retrieve irrelevant ones. Evaluate actual text, inspect surrounding context and precise verse references, distinguish direct vs indirect connections, and do not claim completeness. Source and target links are preserved; output passages should cite their translation.

The legacy `search.py` and `question_search.py` remain supported with `$BIBLE_DB`; the latter is Russian-only and uses its embedded four-verse passage index.

## Experimental parent–child topic

For a request about relationships between parents and children, supplement the semantic search with the experimental thematic prototype and literal searches. Run:

```bash
python3 "$SKILL_DIR/scripts/topic_search.py" --database "$BIBLE_DB" --translation russyn
```

Use `--translation kjv` for KJV. The result is a curated list of 15 passages grouped by category and fetched from the source text; it is not an exhaustive list or embedding-based semantic search. Use `--candidates` to request additional literal keyword matches for assessment, but never assert that unreviewed lexical candidates are relevant. Inspect surrounding context as necessary and explain indirect parallels, such as a parable or theological analogy. If the user asks for all passages, explicitly acknowledge incompleteness and combine this seed list with additional searches; do not claim completeness.

## Source-text and Dutch edition notes

The unified file contains Hebrew/Aramaic WLC (39 Old Testament books), Greek UGNT v0.34 (27 New Testament books), and Dutch *De Heilige Schrift 1917* (66 books). Their source versions, license notices, USFM, source annotations and mapping provenance are preserved. WLC text is public domain and its annotations use CC BY-SA 3.0; UGNT uses CC BY-SA 4.0; the Dutch source declares public domain. Preserve attribution and applicable license terms when sharing or adapting material. Search these editions with the unified commands above. The legacy `original_search.py` can also use `$BIBLE_DB` for both `--database` and `--bible-database`.

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
