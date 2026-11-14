#!/usr/bin/env python3
"""Create a resumable multilingual passage vector index using multilingual E5 ONNX."""
import argparse,hashlib,json,sqlite3,time,unicodedata
from pathlib import Path
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

MODEL_ID='intfloat/multilingual-e5-small'
MODEL_REVISION='614241f622f53c4eeff9890bdc4f31cfecc418b3'
MODEL_SHA256='dd476dd0c2514e9b9be83aeb3853fac0763e0bdf4a71645407587d77c48a2d88'
TOKENIZER_SHA256='0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39'

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def embed(session,encoded):
 n=len(encoded);maxlen=max(len(e) for e in encoded)
 ids=np.full((n,maxlen),1,dtype=np.int64);mask=np.zeros((n,maxlen),dtype=np.int64)
 for i,e in enumerate(encoded):ids[i,:len(e)]=e;mask[i,:len(e)]=1
 h=session.run(None,{'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)})[0]
 y=(h*mask[:,:,None]).sum(axis=1)/np.maximum(mask.sum(axis=1)[:,None],1)
 y=y/np.maximum(np.linalg.norm(y,axis=1,keepdims=True),1e-12)
 return y.astype('<f4')

def build(database,model,tokenizer,output,batch,threads):
 dbsha=sha(database)
 if sha(model)!=MODEL_SHA256 or sha(tokenizer)!=TOKENIZER_SHA256:raise ValueError('Unexpected model/tokenizer checksum')
 source=sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True)
 meta=dict(source.execute('select key,value from metadata'))
 if meta.get('unified_format')!='bible-unified-v1':raise ValueError('Unexpected Bible database')
 if output.exists():
  db=sqlite3.connect(output);m=dict(db.execute('select key,value from semantic_metadata'))
  if m.get('bible_sha256')!=dbsha or m.get('model_sha256')!=MODEL_SHA256:raise ValueError('Resume DB mismatch')
  if m.get('original_preprocess')!='strip_combining_marks_v1':
   db.execute("DELETE FROM semantic_vectors WHERE passage_id IN (SELECT id FROM semantic_passage WHERE translation IN ('hboWLC','ugnt'))")
   db.execute("INSERT OR REPLACE INTO semantic_metadata VALUES ('original_preprocess','strip_combining_marks_v1')");db.commit()
 else:
  db=sqlite3.connect(output)
  db.executescript('''CREATE TABLE semantic_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
  CREATE TABLE semantic_passage(id INTEGER PRIMARY KEY,translation TEXT NOT NULL,book TEXT NOT NULL,chapter INTEGER NOT NULL,start INTEGER NOT NULL,end INTEGER NOT NULL,text TEXT NOT NULL);
  CREATE TABLE semantic_vectors(passage_id INTEGER NOT NULL,part INTEGER NOT NULL,vector BLOB NOT NULL,PRIMARY KEY(passage_id,part));
  CREATE INDEX semantic_translation ON semantic_passage(translation,book,chapter,start);
  ''')
  db.executemany('insert into semantic_metadata values (?,?)',[('format','bible-e5-onnx-v1'),('model',MODEL_ID),('model_revision',MODEL_REVISION),('model_sha256',MODEL_SHA256),('tokenizer_sha256',TOKENIZER_SHA256),('model_license','MIT'),('bible_sha256',dbsha),('query_prefix','query: '),('passage_prefix','passage: '),('dimension','384'),('normalization','L2'),('max_tokens','240'),('window','up to 4 verses, stride 2; overlapping token chunks for long windows'),('state','building')])
  n=0
  # Preserve the exact existing three-language passage windows.
  for lang,b,ch,start,end,text in source.execute('select translation,book,chapter,start,end,text from multilang_passage order by id'):
   n+=1;db.execute('insert into semantic_passage values (?,?,?,?,?,?,?)',(n,lang,b,ch,start,end,text))
  for lang in ('hboWLC','ugnt'):
   rows=source.execute('select book,chapter,verse,text from verse where source=? order by rowid',(lang,)).fetchall();group=[];cur=None
   def write_group():
    nonlocal n
    for i in range(0,len(group),2):
     window=group[i:i+4]
     if window:
      n+=1;db.execute('insert into semantic_passage values (?,?,?,?,?,?,?)',(n,lang,cur[0],cur[1],window[0][0],window[-1][0],' '.join(x[1] for x in window)))
   for b,ch,v,text in rows:
    if (b,ch)!=cur or (group and v!=group[-1][0]+1):
     if group:write_group()
     cur=(b,ch);group=[]
    group.append((v,text))
   if group:write_group()
  db.execute("INSERT OR REPLACE INTO semantic_metadata VALUES ('original_preprocess','strip_combining_marks_v1')");db.commit()
 t=Tokenizer.from_file(str(tokenizer));t.enable_truncation(max_length=240,stride=32)
 prefix=t.encode('passage: ').ids[1:-1]
 pending=[]
 completed=set(db.execute('select passage_id,part from semantic_vectors'))
 for pid,text,lang in db.execute('select id,text,translation from semantic_passage order by id'):
  if lang in ('hboWLC','ugnt'):
   text=''.join(c for c in unicodedata.normalize('NFD',text) if not unicodedata.combining(c))
  enc=t.encode('passage: '+text)
  if (pid,0) not in completed:pending.append((pid,0,enc.ids))
  for i,sub in enumerate(enc.overflowing,1):
   if (pid,i) not in completed:pending.append((pid,i,[sub.ids[0]]+prefix+sub.ids[1:]))
 pending.sort(key=lambda x:len(x[2]))
 opts=ort.SessionOptions();opts.intra_op_num_threads=threads;opts.inter_op_num_threads=1
 session=ort.InferenceSession(str(model),sess_options=opts,providers=['CPUExecutionProvider'])
 print('model ready; chunks',len(pending),'passages',db.execute('select count(*) from semantic_passage').fetchone()[0],flush=True)
 start=time.monotonic()
 for i in range(0,len(pending),batch):
  rows=pending[i:i+batch];vectors=embed(session,[x[2] for x in rows])
  db.executemany('INSERT INTO semantic_vectors VALUES (?,?,?)',((row[0],row[1],vector.tobytes()) for row,vector in zip(rows,vectors)))
  if i//batch%30==0:
   db.commit();print('encoded',min(i+batch,len(pending)),'/',len(pending),'elapsed_seconds',round(time.monotonic()-start),flush=True)
 db.execute("update semantic_metadata set value='complete' where key='state'");db.commit()
 print('counts',db.execute('select translation,count(*) from semantic_passage group by translation').fetchall(),flush=True)
 print('vectors',db.execute('select count(*) from semantic_vectors').fetchone()[0],'integrity',db.execute('pragma integrity_check').fetchone()[0],flush=True)
 db.close();source.close()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--model',type=Path,required=True);p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--batch',type=int,default=24);p.add_argument('--threads',type=int,default=4);a=p.parse_args();build(a.database,a.model,a.tokenizer,a.output,a.batch,a.threads)
if __name__=='__main__':main()
