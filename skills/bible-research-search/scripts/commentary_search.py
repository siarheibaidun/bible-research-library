#!/usr/bin/env python3
"""Retrieve Matthew Henry commentary by a Bible verse or English keywords."""
import argparse
import json
from pathlib import Path
import re
import sqlite3


def connect(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    meta = dict(db.execute('SELECT key,value FROM metadata'))
    if meta.get('format') != 'mhc-sqlite-v1' or meta.get('source') != 'Matthew Henry Commentary, SWORD MHC':
        raise ValueError('Not a supported Matthew Henry database')
    return db


def show_comment(db, row, max_chars):
    cid = row['id']
    refs = [dict(x) for x in db.execute('SELECT book,chapter,verse FROM comment_verses WHERE comment_id=? ORDER BY book,chapter,verse', (cid,))]
    crossrefs = [x[0] for x in db.execute('SELECT osis_ref FROM comment_crossrefs WHERE comment_id=? ORDER BY osis_ref', (cid,))]
    text = row['text']
    return {'id': cid, 'kjv_verses': refs, 'cross_references': crossrefs,
            'text': text[:max_chars], 'total_characters': len(text),
            'truncated': len(text) > max_chars}


def verse(db, translation, book, chapter, number, max_chars):
    if translation == 'russyn':
        rows = db.execute('''SELECT kjv_book,kjv_chapter,kjv_verse,ru_part,kjv_part,status,evidence,mapping_id FROM verse_mapping WHERE ru_book=? AND ru_chapter=? AND ru_verse=? ORDER BY kjv_book,kjv_chapter,kjv_verse''', (book, chapter, number))
        mapped = [dict(x) for x in rows]
    else:
        mapped = [{'kjv_book': book, 'kjv_chapter': chapter, 'kjv_verse': number, 'status': 'original_kjv'}]
    found = {}
    for target in mapped:
        for row in db.execute('''SELECT c.id,c.text FROM comments c JOIN comment_verses v ON c.id=v.comment_id WHERE v.book=? AND v.chapter=? AND v.verse=? ORDER BY c.id''', (target['kjv_book'], target['kjv_chapter'], target['kjv_verse'])):
            if row['id'] not in found:
                found[row['id']] = show_comment(db, row, max_chars)
    return {'source': 'Matthew Henry Commentary, SWORD MHC v2.2', 'requested': {'translation': translation, 'book': book, 'chapter': chapter, 'verse': number}, 'kjv_mappings': mapped, 'comments': list(found.values()), 'note': 'No numbered verse mapping established' if not mapped else ('No commentary entry for mapped verse' if not found else None)}


def search(db, query, limit, offset):
    # FTS5 query is a literal phrase, not raw query syntax.
    if not re.search(r'\w', query):
        raise ValueError('Search must contain letters or digits')
    phrase = '"' + query.replace('"', '""') + '"'
    total = db.execute('SELECT count(*) FROM comment_search WHERE comment_search MATCH ?', (phrase,)).fetchone()[0]
    rows = db.execute('''SELECT c.id, snippet(comment_search,0,'[',']',' … ',28) AS excerpt FROM comment_search JOIN comments c ON c.id=comment_search.rowid WHERE comment_search MATCH ? ORDER BY rank, c.id LIMIT ? OFFSET ?''', (phrase, limit, offset)).fetchall()
    matches = []
    for row in rows:
        refs = [dict(x) for x in db.execute('SELECT book,chapter,verse FROM comment_verses WHERE comment_id=? ORDER BY book,chapter,verse', (row['id'],))]
        matches.append({'id': row['id'], 'excerpt': row['excerpt'], 'kjv_verses': refs})
    return {'source':'Matthew Henry Commentary, SWORD MHC v2.2', 'mode':'English FTS5 literal token phrase', 'query':query, 'total':total, 'offset':offset, 'results':matches}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('verse'); p.add_argument('--translation',choices=['russyn','kjv'],required=True)
    p.add_argument('--book', required=True, help='USFM book code, e.g. JHN or PSA')
    p.add_argument('--chapter', required=True, type=int); p.add_argument('--verse', required=True, type=int)
    p.add_argument('--max-chars', type=int, default=12000)
    q = sub.add_parser('search'); q.add_argument('query'); q.add_argument('--limit', type=int, default=10); q.add_argument('--offset', type=int, default=0)
    a = parser.parse_args()
    if a.action == 'verse' and (a.chapter < 1 or a.verse < 1 or not 1 <= a.max_chars <= 2000000): parser.error('chapter, verse and max-chars must be positive; max-chars <= 2000000')
    if a.action == 'search' and (not 1 <= a.limit <= 50 or a.offset < 0): parser.error('limit must be 1–50 and offset >= 0')
    with connect(a.database) as db:
        result = verse(db, a.translation, a.book.upper(), a.chapter, a.verse, a.max_chars) if a.action == 'verse' else search(db, a.query, a.limit, a.offset)
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
