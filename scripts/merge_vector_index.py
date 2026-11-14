#!/usr/bin/env python3
"""Add validated semantic vectors and offline inference assets to the unified Bible."""
import argparse,hashlib,os,sqlite3,tempfile,zipfile
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def merge(base,vectors,model,tokenizer,wheels,out):
 if out.exists():raise FileExistsError(out)
 source=sqlite3.connect(base.resolve().as_uri()+'?mode=ro',uri=True);vec=sqlite3.connect(vectors.resolve().as_uri()+'?mode=ro',uri=True)
 m=dict(vec.execute('select key,value from semantic_metadata'))
 if m.get('state')!='complete' or m.get('bible_sha256')!=sha(base):raise ValueError('Incomplete vectors or Bible snapshot mismatch')
 if m.get('model_sha256')!=sha(model) or m.get('tokenizer_sha256')!=sha(tokenizer):raise ValueError('Model/tokenizer mismatch')
 if vec.execute('select count(*) from semantic_passage p where not exists(select 1 from semantic_vectors v where v.passage_id=p.id)').fetchone()[0]:raise ValueError('Passages without vectors')
 if vec.execute('select count(*) from semantic_vectors where length(vector)<>1536').fetchone()[0]:raise ValueError('Invalid vector dimensions')
 if vec.execute('pragma integrity_check').fetchone()[0]!='ok' or source.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Input failed integrity check')
 out.parent.mkdir(parents=True,exist_ok=True);fd,tmp=tempfile.mkstemp(prefix='.semantic-',suffix='.sqlite3',dir=out.parent);os.close(fd);tmp=Path(tmp)
 try:
  db=sqlite3.connect(tmp);source.backup(db);db.execute('attach database ? as vec',(str(vectors.resolve()),))
  db.executescript('''CREATE TABLE semantic_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    INSERT INTO semantic_metadata SELECT * FROM vec.semantic_metadata;
    CREATE TABLE semantic_passage(id INTEGER PRIMARY KEY,translation TEXT NOT NULL,book TEXT NOT NULL,chapter INTEGER NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,text TEXT NOT NULL);
    INSERT INTO semantic_passage SELECT * FROM vec.semantic_passage;
    CREATE TABLE semantic_vectors(passage_id INTEGER NOT NULL,part INTEGER NOT NULL,vector BLOB NOT NULL,PRIMARY KEY(passage_id,part));
    INSERT INTO semantic_vectors SELECT * FROM vec.semantic_vectors;
    CREATE INDEX semantic_translation ON semantic_passage(translation,book,chapter,start);
    CREATE TABLE semantic_assets(name TEXT PRIMARY KEY,sha256 TEXT NOT NULL,data BLOB NOT NULL);
  ''')
  missing=db.execute('''SELECT count(*) FROM multilang_passage p LEFT JOIN semantic_passage s ON p.id=s.id WHERE s.id IS NULL OR p.translation<>s.translation OR p.book<>s.book OR p.chapter<>s.chapter OR p.start<>s.start OR p.end<>s.end OR p.text<>s.text''').fetchone()[0]
  if missing:raise ValueError(f'Existing multilingual passage IDs differ: {missing}')
  for lang in ('russyn','kjv'):
   missing=db.execute('''SELECT count(*) FROM location v WHERE v.translation=? AND v.verse>0 AND NOT EXISTS (SELECT 1 FROM semantic_passage p WHERE p.translation=v.translation AND p.book=v.book AND p.chapter=v.chapter AND v.verse BETWEEN p.start AND p.end)''',(lang,)).fetchone()[0]
   if missing:raise ValueError(f'{lang}: {missing} unindexed verses')
  for lang in ('nld1917','hboWLC','ugnt'):
   missing=db.execute('''SELECT count(*) FROM verse v WHERE v.source=? AND NOT EXISTS (SELECT 1 FROM semantic_passage p WHERE p.translation=v.source AND p.book=v.book AND p.chapter=v.chapter AND v.verse BETWEEN p.start AND p.end)''',(lang,)).fetchone()[0]
   if missing:raise ValueError(f'{lang}: {missing} unindexed verses')
  n=db.execute('select count(*) from semantic_passage').fetchone()[0]
  db.executemany('insert into semantic_metadata values (?,?)',[('passage_count',str(n)),('model_url','https://huggingface.co/intfloat/multilingual-e5-small'),('model_variant','onnx/model_qint8_avx512_vnni.onnx'),('runtime_requirements','Python 3.12, Linux x86-64 AVX-512 VNNI'),('coverage','All indexed numbered verses in the five source editions')])
  db.executemany('insert into semantic_assets values (?,?,?)',[(name,sha(path),path.read_bytes()) for name,path in [('model.onnx',model),('tokenizer.json',tokenizer),('runtime_wheels.zip',wheels)]])
  db.execute('insert into metadata values (?,?)',('semantic_index','bible-e5-onnx-v1'));db.commit()
  if db.execute('pragma integrity_check').fetchone()[0]!='ok':raise ValueError('Output failed integrity check')
  print('passages',n,'vectors',db.execute('select count(*) from semantic_vectors').fetchone()[0],flush=True);db.close();os.replace(tmp,out)
 finally:
  tmp.unlink(missing_ok=True);source.close();vec.close()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bible',type=Path,required=True);p.add_argument('--vectors',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--wheels',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();merge(a.bible,a.vectors,a.model,a.tokenizer,a.wheels,a.output)
if __name__=='__main__':main()
