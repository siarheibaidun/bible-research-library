#!/usr/bin/env python3
"""Look up MHC commentary using KJV or mapped Russian Synodal verse numbers."""
import argparse
import json
import sqlite3
from pathlib import Path

def lookup(database, translation, book, chapter, verse):
    with sqlite3.connect('file:' + str(database.resolve()) + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        if translation == 'russyn':
            mapped = db.execute('SELECT kjv_book,kjv_chapter,kjv_verse,ru_part,kjv_part,status,evidence,mapping_id FROM verse_mapping WHERE ru_book=? AND ru_chapter=? AND ru_verse=? ORDER BY kjv_book,kjv_chapter,kjv_verse', (book,chapter,verse)).fetchall()
            mappings = [dict(x) for x in mapped]
        else:
            mappings = [dict(kjv_book=book,kjv_chapter=chapter,kjv_verse=verse,status='original_kjv',mapping_id=None)]
        found = {}
        for m in mappings:
            rows = db.execute('''SELECT c.id,c.text FROM comments c JOIN comment_verses v ON v.comment_id=c.id WHERE v.book=? AND v.chapter=? AND v.verse=? ORDER BY c.id''',(m['kjv_book'],m['kjv_chapter'],m['kjv_verse'])).fetchall()
            for row in rows:
                cid = row['id']
                if cid not in found:
                    refs = [dict(x) for x in db.execute('SELECT book,chapter,verse FROM comment_verses WHERE comment_id=? ORDER BY book,chapter,verse',(cid,))]
                    crossrefs = [x[0] for x in db.execute('SELECT osis_ref FROM comment_crossrefs WHERE comment_id=? ORDER BY osis_ref',(cid,))]
                    found[cid] = {'id':cid,'kjv_verses':refs,'cross_references':crossrefs,'text':row['text']}
        return {'requested':{'translation':translation,'book':book,'chapter':chapter,'verse':verse},'kjv_mappings':mappings,'comments':list(found.values()),'note': 'No mapping available' if translation=='russyn' and not mappings else None}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--db',type=Path,required=True)
    p.add_argument('--translation',choices=['kjv','russyn'],required=True)
    p.add_argument('--book',required=True,help='USFM book code, e.g. JHN or PSA')
    p.add_argument('--chapter',required=True,type=int); p.add_argument('--verse',required=True,type=int)
    a=p.parse_args()
    print(json.dumps(lookup(a.db,a.translation,a.book.upper(),a.chapter,a.verse),ensure_ascii=False,indent=2))
if __name__=='__main__': main()
