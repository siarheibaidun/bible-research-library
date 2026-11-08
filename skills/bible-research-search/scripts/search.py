#!/usr/bin/env python3
"""Search a Bible Research Library SQLite snapshot and inspect mapped verses."""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path
from lookup_verse import ALIASES, NAMES, RUSSIAN_NAMES, normalize, read_note


def open_db(path):
    if not path.is_file(): raise ValueError(f'Bible database not found: {path}')
    db = sqlite3.connect(f'{path.resolve().as_uri()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    meta = dict(db.execute('SELECT key,value FROM metadata'))
    required = {'russyn_archive_sha256':'9af20fe73fff9370acc8fd03cc0ffa718e1cf107d83fc401d41dcadc6c4e4a88',
                'kjv_archive_sha256':'069646cd8722f6d57750d3b35d378181f9446dc3abeb81a554fd51b57c928689'}
    if any(meta.get(k)!=v for k,v in required.items()):
        db.close(); raise ValueError('Unexpected Bible database source editions.')
    return db, meta


def book_code(name):
    code = ALIASES.get(normalize(name))
    if not code: raise ValueError(f'Unknown book: {name}')
    return code


def parse_ref(text):
    m=re.fullmatch(r'\s*(.+?)\s+(\d+):(\d+)\s*',text)
    if not m: raise ValueError('Use a reference such as John 3:16 or Псалом 3:1.')
    code=book_code(m.group(1));c=int(m.group(2));v=int(m.group(3))
    if c<1 or (v==0 and code!='PSA'): raise ValueError('Invalid chapter or verse; only Psalm headings use verse 0.')
    return code,c,v


def fmt_ref(lang,book,chapter,verse):
    name=RUSSIAN_NAMES.get(book,NAMES[book]) if lang=='russyn' else NAMES[book]
    return f'{name} {chapter}:{verse}' if verse else f'{name} {chapter} heading'


def convert(row):
    data=dict(row); data.pop('folded',None)
    data['reference']=fmt_ref(data['translation'],data['book'],data['chapter'],data['verse'])
    notes=json.loads(data.get('notes','[]')); output=[]
    for item in notes:
        result=read_note(item['raw_usfm'])
        output.append({'type':item.get('type','note'),'reference':result[0] if result else None,
                       'text':result[1] if result else None,'raw_usfm':item['raw_usfm']})
    data['notes']=output
    return data


def search(db, query, translation, book=None, limit=20, offset=0):
    if not query.strip(): raise ValueError('Search text must not be empty.')
    if not 1<=limit<=100 or offset<0: raise ValueError('Limit must be 1–100 and offset must be nonnegative.')
    where=['instr(folded, ?) > 0', 'verse > 0']; args=[query.casefold()]
    if translation!='both': where.append('translation = ?');args.append(translation)
    if book: where.append('book = ?');args.append(book_code(book))
    sql=' AND '.join(where)
    total=db.execute('SELECT count(*) FROM location WHERE '+sql,args).fetchone()[0]
    rows=[convert(x) for x in db.execute('SELECT * FROM location WHERE '+sql,args)]
    order={book:i for i,book in enumerate(NAMES)}
    rows.sort(key=lambda x:(order[x['book']],x['chapter'],x['verse'],x['translation']))
    return {'query':query,'matching':'case-insensitive literal substring in verse text; not notes',
            'total':total,'offset':offset,'limit':limit,'results':rows[offset:offset+limit]}


def verse(db, reference, translation, parallel=False):
    code,c,v=parse_ref(reference)
    row=db.execute('SELECT * FROM location WHERE translation=? AND book=? AND chapter=? AND verse=?',(translation,code,c,v)).fetchone()
    if row is None: raise ValueError('Reference not found in the selected translation.')
    output={'selected':convert(row)}
    if parallel:
        members=db.execute('SELECT relation_id FROM member WHERE translation=? AND book=? AND chapter=? AND verse=?',(translation,code,c,v)).fetchall()
        groups=[]
        for x in members:
            r=db.execute('SELECT * FROM relation WHERE id=?',(x['relation_id'],)).fetchone()
            entries=db.execute('SELECT * FROM member WHERE relation_id=? ORDER BY translation,chapter,verse',(x['relation_id'],)).fetchall()
            locations=[]
            for e in entries:
                loc=db.execute('SELECT * FROM location WHERE translation=? AND book=? AND chapter=? AND verse=?',(e['translation'],e['book'],e['chapter'],e['verse'])).fetchone()
                if loc is None: raise ValueError('Mapped location is absent from the snapshot.')
                value=convert(loc);value['part']=e['part'];locations.append(value)
            try:evidence=json.loads(r['evidence'])
            except (ValueError,TypeError):evidence=r['evidence']
            groups.append({'status':r['status'],'evidence':evidence,'map_id':r['map_id'],'locations':locations})
        output['mapping_groups']=groups
        output['mapping_warning']='Source-derived and same-reference mappings are not individually text-verified. Verse parts and headings may show a larger full text.'
    return output


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True)
    sub=p.add_subparsers(dest='action',required=True)
    sp=sub.add_parser('search');sp.add_argument('query');sp.add_argument('--translation',choices=('russyn','kjv','both'),default='both');sp.add_argument('--book');sp.add_argument('--limit',type=int,default=20);sp.add_argument('--offset',type=int,default=0)
    vp=sub.add_parser('verse');vp.add_argument('reference');vp.add_argument('--translation',choices=('russyn','kjv'),required=True);vp.add_argument('--parallel',action='store_true')
    a=p.parse_args()
    try:
        db,metadata=open_db(a.database)
        try:result=search(db,a.query,a.translation,a.book,a.limit,a.offset) if a.action=='search' else verse(db,a.reference,a.translation,a.parallel)
        finally:db.close()
        result['provenance']=metadata
        print(json.dumps(result,ensure_ascii=False,indent=2))
    except (OSError,ValueError,sqlite3.Error,json.JSONDecodeError) as e:
        print(f'Error: {e}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
