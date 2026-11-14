#!/usr/bin/env python3
"""Search Hebrew WLC, Greek UGNT and Dutch 1917 and retrieve candidate KJV links."""
import argparse,json,sqlite3,unicodedata
from pathlib import Path

def fold(text):return ''.join(c for c in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(c))
def connect(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    if dict(db.execute('select key,value from metadata')).get('format')!='original-index-v1':raise ValueError('Unexpected original-language database')
    return db

def verse(db,source,book,chapter,number,with_tokens=False):
    row=db.execute('select * from verse where source=? and book=? and chapter=? and verse=?',(source,book,chapter,number)).fetchone()
    if row is None:return {'source':source,'book':book,'chapter':chapter,'verse':number,'found':False}
    v=dict(row);v.pop('folded');v.pop('raw_usfm'); tokens=json.loads(v.pop('tokens'));v['notes']=json.loads(v['notes']);
    if with_tokens:v['tokens']=tokens
    maps=[dict(x) for x in db.execute('select kjv_book,kjv_chapter,kjv_verse,kjv_part,status,evidence from mapping where source=? and book=? and chapter=? and verse=?',(source,book,chapter,number))]
    unresolved=[x[0] for x in db.execute('select reason from unresolved where source=? and book=? and chapter=? and verse=?',(source,book,chapter,number))]
    return {'found':True,'verse':v,'kjv_mappings':maps,'unresolved':unresolved,'mapping_warning':'Candidate mappings; scope, parts, headings and textual equivalence may require verification.'}

def cross(db,bible,lang,book,chapter,number,sources):
    expected=db.execute("select value from metadata where key='kjv_source_sha256'").fetchone()[0]
    actual=bible.execute("select value from metadata where key='kjv_archive_sha256'").fetchone()
    if not actual or actual[0]!=expected:raise ValueError('KJV index source does not match mapping source')
    kjv=[];ru_rel=[]
    if lang=='kjv':kjv=[(book,chapter,number,None,'original_kjv')]
    else:
        ids=bible.execute('select relation_id from member where translation=? and book=? and chapter=? and verse=?',(lang,book,chapter,number)).fetchall()
        for rid, in ids:
            rel_row=bible.execute('select status,evidence,map_id from relation where id=?',(rid,)).fetchone()
            rel=dict(zip(('status','evidence','map_id'),rel_row))
            for b,c,v,part in bible.execute("select book,chapter,verse,part from member where relation_id=? and translation='kjv'",(rid,)):
                kjv.append((b,c,v,part,rel['status']));ru_rel.append({'kjv_book':b,'kjv_chapter':c,'kjv_verse':v,'kjv_part':part,'status':rel['status'],'map_id':rel['map_id'],'evidence':rel['evidence']})
    results=[];seen=set()
    for b,c,v,part,status in kjv:
        for source in sources:
            for row in db.execute('''select source,book,chapter,verse,kjv_book,kjv_chapter,kjv_verse,kjv_part,status,evidence from mapping where source=? and kjv_book=? and kjv_chapter=? and kjv_verse=?''',(source,b,c,v)):
                item=dict(row); key=(source,item['book'],item['chapter'],item['verse'],b,c,v,item['kjv_part'])
                if key in seen:continue
                seen.add(key);result=verse(db,source,item['book'],item['chapter'],item['verse']);results.append({'kjv_bridge':{'book':b,'chapter':c,'verse':v,'part':part,'source_mapping_status':status},'target_mapping':item,'target':result['verse']})
    return {'requested':{'translation':lang,'book':book,'chapter':chapter,'verse':number},'russian_kjv_mappings':ru_rel,'results':results,'warning':'Mappings are candidate verse relationships through KJV, not word alignments or proof of semantic equivalence. Partial/heading relationships may return full verses.'}

def search(db,source,query,limit,offset):
    q=fold(query)
    if not q.strip():raise ValueError('Empty query')
    total=db.execute('select count(*) from verse where source=? and instr(folded,?)>0',(source,q)).fetchone()[0]
    rows=[dict(r) for r in db.execute('select source,book,chapter,verse,text from verse where source=? and instr(folded,?)>0 order by rowid limit ? offset ?',(source,q,limit,offset))]
    return {'source':source,'query':query,'matching':'case- and diacritic-insensitive literal substring; not a lemma or semantic search','total':total,'offset':offset,'results':rows}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);sub=p.add_subparsers(dest='action',required=True)
    v=sub.add_parser('verse');v.add_argument('--source',choices=['hboWLC','ugnt','nld1917'],required=True);v.add_argument('--book',required=True);v.add_argument('--chapter',type=int,required=True);v.add_argument('--verse',type=int,required=True);v.add_argument('--tokens',action='store_true')
    s=sub.add_parser('search');s.add_argument('--source',choices=['hboWLC','ugnt','nld1917'],required=True);s.add_argument('query');s.add_argument('--limit',type=int,default=20);s.add_argument('--offset',type=int,default=0)
    c=sub.add_parser('cross');c.add_argument('--bible-database',type=Path,required=True);c.add_argument('--from-translation',choices=['kjv','russyn'],required=True);c.add_argument('--book',required=True);c.add_argument('--chapter',type=int,required=True);c.add_argument('--verse',type=int,required=True);c.add_argument('--source',choices=['hboWLC','ugnt','nld1917'],action='append')
    a=p.parse_args()
    if a.action=='search' and (a.limit<1 or a.limit>100 or a.offset<0):p.error('limit 1–100 and nonnegative offset required')
    with connect(a.database) as db:
        if a.action=='verse':r=verse(db,a.source,a.book.upper(),a.chapter,a.verse,a.tokens)
        elif a.action=='search':r=search(db,a.source,a.query,a.limit,a.offset)
        else:
            with sqlite3.connect(a.bible_database.resolve().as_uri()+'?mode=ro',uri=True) as bible:r=cross(db,bible,a.from_translation,a.book.upper(),a.chapter,a.verse,a.source or ['hboWLC','ugnt','nld1917'])
    print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
