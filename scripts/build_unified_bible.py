#!/usr/bin/env python3
"""Combine the project's Bible snapshots into one compatible SQLite database."""
import argparse,hashlib,os,sqlite3,tempfile
from pathlib import Path

EXPECTED_RU='9af20fe73fff9370acc8fd03cc0ffa718e1cf107d83fc401d41dcadc6c4e4a88'
EXPECTED_KJV='069646cd8722f6d57750d3b35d378181f9446dc3abeb81a554fd51b57c928689'

def uri(p):return p.resolve().as_uri()+'?mode=ro'
def checksum(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
def meta(db):return dict(db.execute('SELECT key,value FROM metadata'))
def build(base,original,passages,out):
 if out.exists():raise FileExistsError(out)
 out.parent.mkdir(parents=True,exist_ok=True)
 sources=[sqlite3.connect(uri(p),uri=True) for p in (base,original,passages)]
 try:
  m0,m1,m2=map(meta,sources)
  if (m0.get('russyn_archive_sha256'),m0.get('kjv_archive_sha256'))!=(EXPECTED_RU,EXPECTED_KJV):raise ValueError('Unexpected Bible base editions')
  if m1.get('format')!='original-index-v1' or m1.get('kjv_source_sha256')!=EXPECTED_KJV:raise ValueError('Original index is not compatible with the KJV snapshot')
  if m2.get('source_sha256')!=EXPECTED_RU:raise ValueError('Russian passage index source differs')
  for db in sources:
   if db.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Source database integrity check failed')
  fd,temp=tempfile.mkstemp(prefix='.unified-',suffix='.sqlite3',dir=out.parent);os.close(fd);p=Path(temp)
  try:
   db=sqlite3.connect(p);sources[0].backup(db)
   db.execute('ATTACH DATABASE ? AS original',(str(original.resolve()),));db.execute('ATTACH DATABASE ? AS passages',(str(passages.resolve()),))
   db.executescript('''
   CREATE TABLE original_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
   INSERT INTO original_metadata SELECT * FROM original.metadata;
   CREATE TABLE passage_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
   INSERT INTO passage_metadata SELECT * FROM passages.metadata;
   CREATE TABLE verse(source TEXT,book TEXT,chapter INTEGER,verse INTEGER,text TEXT,folded TEXT,raw_usfm TEXT,tokens TEXT,notes TEXT,source_file TEXT,PRIMARY KEY(source,book,chapter,verse));
   INSERT INTO verse SELECT * FROM original.verse;
   CREATE TABLE mapping(source TEXT,book TEXT,chapter INTEGER,verse INTEGER,kjv_book TEXT,kjv_chapter INTEGER,kjv_verse INTEGER,kjv_part TEXT,status TEXT,evidence TEXT,UNIQUE(source,book,chapter,verse,kjv_book,kjv_chapter,kjv_verse,kjv_part,status));
   INSERT INTO mapping SELECT * FROM original.mapping;
   CREATE INDEX map_kjv ON mapping(kjv_book,kjv_chapter,kjv_verse);
   CREATE INDEX map_source ON mapping(source,book,chapter,verse);
   CREATE TABLE unresolved(source TEXT,book TEXT,chapter INTEGER,verse INTEGER,reason TEXT);
   INSERT INTO unresolved SELECT * FROM original.unresolved;
   CREATE TABLE rule_issues(line INTEGER,rule TEXT,reason TEXT);
   INSERT INTO rule_issues SELECT * FROM original.rule_issues;
   CREATE TABLE passage(id INTEGER PRIMARY KEY,book TEXT,chapter INTEGER,start INTEGER,end INTEGER,text TEXT);
   INSERT INTO passage SELECT * FROM passages.passage;
   CREATE VIRTUAL TABLE passage_fts USING fts5(text,content='passage',content_rowid='id',tokenize='unicode61');
   INSERT INTO passage_fts(passage_fts) VALUES('rebuild');
   CREATE TABLE multilang_passage(id INTEGER PRIMARY KEY,translation TEXT,book TEXT,chapter INTEGER,start INTEGER,end INTEGER,text TEXT);
   CREATE VIRTUAL TABLE multilang_fts USING fts5(text,content='multilang_passage',content_rowid='id',tokenize='unicode61');
   ''')
   # Retain original metadata for the historical question_search.py command.
   db.execute('INSERT INTO metadata VALUES (?,?)',('source_sha256',m2['source_sha256']))
   # Edition-specific split verses. These relationships were compared against
   # the imported UGNT/KJV texts; each covers only part of the KJV verse.
   # REV 12:18 also has a textual variant (Greek: he stood; KJV: I stood).
   for book,ch,v,kc,kv,part,explanation in [
    ('3JN',1,14,1,14,'opening','UGNT 3 John 1:14 corresponds to the opening of KJV 1:14; textual comparison'),
    ('3JN',1,15,1,14,'closing','UGNT 3 John 1:15 corresponds to the closing of KJV 1:14; textual comparison'),
    ('REV',12,18,13,1,'opening','UGNT Rev 12:18 corresponds to the opening of KJV Rev 13:1; textual variant: he stood versus I stood'),
    ('REV',13,1,13,1,'remainder','UGNT Rev 13:1 corresponds to the remainder of KJV Rev 13:1; verse scope differs')]:
    if not db.execute('SELECT 1 FROM verse WHERE source=? AND book=? AND chapter=? AND verse=?',('ugnt',book,ch,v)).fetchone():raise ValueError('Expected UGNT verse missing')
    if not db.execute('SELECT 1 FROM location WHERE translation=? AND book=? AND chapter=? AND verse=?',('kjv',book,kc,kv)).fetchone():raise ValueError('Expected KJV verse missing')
    db.execute('DELETE FROM mapping WHERE source=? AND book=? AND chapter=? AND verse=?',('ugnt',book,ch,v))
    db.execute('DELETE FROM unresolved WHERE source=? AND book=? AND chapter=? AND verse=?',('ugnt',book,ch,v))
    db.execute('INSERT INTO mapping VALUES (?,?,?,?,?,?,?,?,?,?)',('ugnt',book,ch,v,book,kc,kv,part,'edition_text_compared_partial',explanation))
   db.executemany('INSERT INTO metadata VALUES (?,?)', [('format','original-index-v1'),('kjv_source_sha256',EXPECTED_KJV),('unified_format','bible-unified-v1'),('unified_base_sha256',checksum(base)),('unified_original_sha256',checksum(original)),('unified_russian_passage_sha256',checksum(passages))])
   # New translations live in the preserved verse table; keep the old location table
   # unchanged so historical RU/KJV search keeps its exact default behavior.
   for lang,table,column in [('russyn','location','translation'),('kjv','location','translation'),('nld1917','verse','source')]:
    rows=db.execute(f'SELECT book,chapter,verse,text FROM {table} WHERE {column}=? AND verse>0 ORDER BY book,chapter,verse',(lang,)).fetchall()
    current=None;group=[]
    def emit():
     for start in range(0,len(group),2):
      window=group[start:start+4]
      if window:
       db.execute('INSERT INTO multilang_passage(translation,book,chapter,start,end,text) VALUES (?,?,?,?,?,?)',(lang,current[0],current[1],window[0][0],window[-1][0],' '.join(x[1] for x in window)))
    for book,ch,v,text in rows:
     if current!=(book,ch) or (group and v!=group[-1][0]+1):
      if group:emit()
      current=(book,ch);group=[]
     group.append((v,text))
    if group:emit()
   db.execute("INSERT INTO multilang_fts(multilang_fts) VALUES('rebuild')")
   db.commit()
   if db.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Unified database integrity check failed')
   counts=db.execute('SELECT source,count(*) FROM verse GROUP BY source').fetchall();n=db.execute('select translation,count(*) from multilang_passage group by translation').fetchall();db.close();os.replace(p,out);print('Original-language/Dutch verses:',counts);print('Multilingual windows:',n)
  except BaseException:
   p.unlink(missing_ok=True);raise
 finally:
  for s in sources:s.close()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bible',type=Path,required=True);p.add_argument('--originals',type=Path,required=True);p.add_argument('--passages',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.bible,a.originals,a.passages,a.output)
if __name__=='__main__':main()
