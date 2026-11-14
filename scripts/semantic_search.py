#!/usr/bin/env python3
"""Hybrid multilingual semantic search of the unified Bible database."""
import argparse,fcntl,hashlib,json,os,platform,re,shutil,sqlite3,subprocess,sys,tempfile,unicodedata,zipfile
from collections import defaultdict
from pathlib import Path

LANGS=('russyn','kjv','nld1917','hboWLC','ugnt')
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for x in iter(lambda:f.read(1024*1024),b''):h.update(x)
 return h.hexdigest()
def get_asset(db,name,dest):
 row=db.execute('select sha256 from semantic_assets where name=?',(name,)).fetchone()
 if not row:raise ValueError('Required semantic model asset is missing: '+name)
 expected=row[0]
 if not dest.is_file() or digest(dest)!=expected:
  data=db.execute('select data from semantic_assets where name=?',(name,)).fetchone()[0]
  tmp=dest.with_suffix(dest.suffix+'.tmp');tmp.write_bytes(data)
  if digest(tmp)!=expected:tmp.unlink(missing_ok=True);raise ValueError('Corrupt asset: '+name)
  os.replace(tmp,dest)
 return dest

def dependencies(db,cache):
 # Bundled wheels allow a fresh Python 3.12 Linux x86-64 session to run offline.
 target=cache/'python'; marker=target/'.complete'
 if not marker.exists():
  wheelzip=get_asset(db,'runtime_wheels.zip',cache/'runtime_wheels.zip');wheels=cache/'wheels';wheels.mkdir(exist_ok=True)
  with zipfile.ZipFile(wheelzip) as z:
   for member in z.infolist():
    if member.is_dir() or Path(member.filename).name!=member.filename or not member.filename.endswith('.whl'):raise ValueError('Invalid bundled wheel archive')
    dest=wheels/member.filename
    if not dest.exists():dest.write_bytes(z.read(member))
  staging=Path(tempfile.mkdtemp(prefix='install-',dir=cache))
  try:
   subprocess.run([sys.executable,'-m','pip','install','--quiet','--no-index','--find-links',str(wheels),'--target',str(staging),'onnxruntime==1.32.0','tokenizers==0.23.3','numpy==2.3.5'],check=True,stdout=subprocess.DEVNULL)
   (staging/'.complete').write_text('ok')
   if target.exists():shutil.rmtree(target)
   os.replace(staging,target)
  finally:
   if staging.exists():shutil.rmtree(staging)
 sys.path.insert(0,str(target))
 import numpy as np
 import onnxruntime as ort
 from tokenizers import Tokenizer
 return np,ort,Tokenizer

def engine(db):
 if platform.system()!='Linux' or platform.machine().lower() not in ('x86_64','amd64') or sys.version_info[:2]!=(3,12):raise RuntimeError('The bundled semantic runtime requires Python 3.12 on Linux x86-64')
 try:flags=Path('/proc/cpuinfo').read_text().lower()
 except OSError:flags=''
 if 'avx512_vnni' not in flags:raise RuntimeError('The bundled quantized model requires AVX-512 VNNI; use a compatible runtime or a portable model build')
 m=dict(db.execute('select key,value from semantic_metadata'))
 if m.get('state')!='complete' or m.get('format')!='bible-e5-onnx-v1':raise ValueError('Semantic index incomplete or unsupported')
 cache=Path(tempfile.gettempdir())/('bible-semantic-'+m['model_sha256'][:16]);cache.mkdir(mode=0o700,parents=True,exist_ok=True)
 with (cache/'setup.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX)
  np,ort,Tokenizer=dependencies(db,cache)
  model=cache/'model.onnx'
  if not model.exists() or digest(model)!=m['model_sha256']:
   if db.execute("select 1 from semantic_assets where name='model.onnx.zip'").fetchone():
    archive=get_asset(db,'model.onnx.zip',cache/'model.onnx.zip')
    with zipfile.ZipFile(archive) as z:
     if z.namelist()!=['model.onnx']:raise ValueError('Invalid model archive')
     tmp=cache/'model.onnx.tmp'
     with z.open('model.onnx') as src,tmp.open('wb') as dst:shutil.copyfileobj(src,dst,1024*1024)
     if digest(tmp)!=m['model_sha256']:tmp.unlink(missing_ok=True);raise ValueError('Corrupt decompressed model')
     os.replace(tmp,model)
   else:model=get_asset(db,'model.onnx',model)
  tokenizer=get_asset(db,'tokenizer.json',cache/'tokenizer.json')
 if digest(model)!=m['model_sha256'] or digest(tokenizer)!=m['tokenizer_sha256']:raise ValueError('Embedding model and index do not match')
 t=Tokenizer.from_file(str(tokenizer));t.enable_truncation(max_length=240)
 opts=ort.SessionOptions();opts.intra_op_num_threads=4;opts.inter_op_num_threads=1
 session=ort.InferenceSession(str(model),sess_options=opts,providers=['CPUExecutionProvider'])
 return np,t,session,m

def search(db,question,languages,limit,terms):
 if not question.strip() or not 1<=limit<=100:raise ValueError('Question must not be empty; limit must be 1–100')
 np,t,session,metadata=engine(db)
 normalized=question
 if re.search('[\u0590-\u05ff\u0370-\u03ff\u1f00-\u1fff]',question):normalized=''.join(c for c in unicodedata.normalize('NFD',question) if not unicodedata.combining(c))
 enc=t.encode('query: '+normalized);ids=np.array([enc.ids],dtype=np.int64);mask=np.ones_like(ids)
 h=session.run(None,{'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)})[0]
 q=(h*mask[:,:,None]).sum(axis=1)/mask.sum(axis=1)[:,None];q=q/np.maximum(np.linalg.norm(q,axis=1,keepdims=True),1e-12);q=q[0].astype('float32')
 placeholders=','.join('?' for _ in languages)
 rows=db.execute(f'''SELECT v.passage_id,v.vector FROM semantic_vectors v JOIN semantic_passage p ON p.id=v.passage_id WHERE p.translation IN ({placeholders}) ORDER BY v.passage_id,v.part''',languages).fetchall()
 if not rows:return {'results':[],'warning':'No vector passages in selected sources'}
 if any(len(r[1]) not in (768,1536) for r in rows):raise ValueError('Invalid semantic vector dimensions')
 matrix=np.vstack([np.frombuffer(r[1],dtype=('<f2' if len(r[1])==768 else '<f4')).astype('float32') for r in rows]);scores=matrix@q
 # Aggregate multiple token chunks by highest similarity for each passage.
 best={}
 for (pid,_),score in zip(rows,scores):
  f=float(score)
  if pid not in best or f>best[pid]:best[pid]=f
 ranked=sorted(best,key=lambda k:(-best[k],k));candidate=ranked[:min(len(ranked),300)]
 # Reciprocal-rank fusion with lexical candidates when terms are supplied.
 fused=defaultdict(float);matched=defaultdict(set)
 for rank,pid in enumerate(candidate):fused[pid]+=1/(60+rank+1)
 for lang,term in terms:
  if lang not in languages or lang not in ('russyn','kjv','nld1917'):continue
  term=term.casefold().strip()
  if not re.fullmatch(r'[^\W_]{3,40}',term,re.UNICODE):raise ValueError('Terms must be individual 3–40 letter/digit prefixes')
  expr='"'+term+'"*'
  # Existing multilang IDs share semantic_passage IDs for these three editions.
  result=db.execute('''SELECT p.id FROM multilang_fts JOIN multilang_passage p ON p.id=multilang_fts.rowid WHERE multilang_fts MATCH ? AND p.translation=? ORDER BY bm25(multilang_fts),p.id LIMIT 150''',(expr,lang)).fetchall()
  for rank,(pid,) in enumerate(result):fused[pid]+=1/(60+rank+1);matched[pid].add(term)
 ordered=sorted(fused,key=lambda pid:(-fused[pid],-best.get(pid,-1),pid))
 results=[]
 for pid in ordered:
  row=db.execute('select * from semantic_passage where id=?',(pid,)).fetchone()
  if row is None:continue
  d=dict(zip(('id','translation','book','chapter','start','end','text'),row));d['vector_similarity']=round(best.get(pid,0),6);d['lexical_terms']=sorted(matched[pid]);d['fusion_score']=round(fused[pid],6);results.append(d)
  if len(results)>=limit:break
 return {'query':question,'query_truncated':bool(enc.overflowing),'translations':languages,'method':'multilingual dense vectors and optional lexical prefix rank fusion','model':metadata['model'],'model_revision':metadata['model_revision'],'indexed_passages':metadata['passage_count'],'warning':'Candidates are not exhaustive. Similarity is not theological certainty. Evaluate passages in context; original-language relevance quality is not independently established.','results':results}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('query');p.add_argument('--translation',action='append',choices=LANGS);p.add_argument('--limit',type=int,default=30);p.add_argument('--ru-term',action='append',default=[]);p.add_argument('--en-term',action='append',default=[]);p.add_argument('--nl-term',action='append',default=[]);a=p.parse_args()
 with sqlite3.connect(a.database.resolve().as_uri()+'?mode=ro',uri=True) as db:
  terms=[*(('russyn',x) for x in a.ru_term),*(('kjv',x) for x in a.en_term),*(('nld1917',x) for x in a.nl_term)];r=search(db,a.query,a.translation or list(LANGS),a.limit,terms)
 print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
