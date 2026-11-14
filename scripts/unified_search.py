#!/usr/bin/env python3
"""Search five Bible texts and map candidate passages via KJV in both directions."""
import argparse,json,re,sqlite3,unicodedata
from collections import defaultdict
from pathlib import Path
from lookup_verse import ALIASES,NAMES,RUSSIAN_NAMES,normalize

LANGS=('russyn','kjv','nld1917','hboWLC','ugnt')
DUTCH=('Genesis Exodus Leviticus Numeri Deuteronomium Jozua Richteren Ruth 1Samuel 2Samuel 1Koningen 2Koningen 1Kronieken 2Kronieken Ezra Nehemia Esther Job Psalmen Spreuken Prediker Hooglied Jesaja Jeremia Klaagliederen Ezechiel Daniel Hosea Joel Amos Obadja Jona Micha Nahum Habakuk Zefanja Haggai Zacharia Maleachi Mattheus Markus Lukas Johannes Handelingen Romeinen 1Korintiers 2Korintiers Galaten Efeziers Filippenzen Kolossenzen 1Tessalonicenzen 2Tessalonicenzen 1Timotheus 2Timotheus Titus Filemon Hebreeen Jakobus 1Petrus 2Petrus 1Johannes 2Johannes 3Johannes Judas Openbaring').split()
def norm(s):return ''.join(c for c in unicodedata.normalize('NFD',normalize(s)) if not unicodedata.combining(c))
ALIASES={norm(k):v for k,v in ALIASES.items()};ALIASES.update({norm(n):code for code,n in zip(NAMES,DUTCH)});ALIASES.update({'psalm':'PSA','psalmen':'PSA','evangelievanjohannes':'JHN','matteus':'MAT','marcus':'MRK','lucas':'LUK','joel':'JOL','ezekiel':'EZK','daniel':'DAN','prediker':'ECC'})
def bookcode(name):
 b=ALIASES.get(norm(name))
 if not b:raise ValueError(f'Unknown book name: {name}')
 return b
def fold(text):return ''.join(c for c in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(c))
def connect(path):
 if not path.is_file():raise ValueError('Unified database not found')
 db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 if dict(db.execute('select key,value from metadata')).get('unified_format')!='bible-unified-v1':raise ValueError('Not a unified Bible index')
 return db

def get(db,lang,b,c,v,tokens=False):
 if lang in ('russyn','kjv'):
  row=db.execute('select translation,book,chapter,verse,text,notes,source_file from location where translation=? and book=? and chapter=? and verse=?',(lang,b,c,v)).fetchone()
  if not row:return None
  x=dict(row);x['notes']=json.loads(x['notes']);return x
 row=db.execute('select source as translation,book,chapter,verse,text,notes,source_file,tokens from verse where source=? and book=? and chapter=? and verse=?',(lang,b,c,v)).fetchone()
 if not row:return None
 x=dict(row);x['notes']=json.loads(x['notes']);word_data=json.loads(x.pop('tokens'))
 if tokens:x['tokens']=word_data
 return x

def anchors(db,lang,b,c,v):
 if lang=='kjv':return [{'book':b,'chapter':c,'verse':v,'part':None,'status':'original_kjv','evidence':'Direct reference'}]
 if lang=='russyn':
  q='''SELECT k.book,k.chapter,k.verse,k.part,s.part AS source_part,r.status,r.evidence,r.map_id FROM member s JOIN relation r ON r.id=s.relation_id JOIN member k ON k.relation_id=r.id AND k.translation='kjv' WHERE s.translation='russyn' AND s.book=? AND s.chapter=? AND s.verse=?'''
  return [dict(x) for x in db.execute(q,(b,c,v))]
 q='''SELECT kjv_book as book,kjv_chapter as chapter,kjv_verse as verse,kjv_part as part,status,evidence FROM mapping WHERE source=? AND book=? AND chapter=? AND verse=?'''
 return [dict(x) for x in db.execute(q,(lang,b,c,v))]

def targets(db,target,a):
 b,c,v=a['book'],a['chapter'],a['verse']
 if target=='kjv':
  return [({'translation':'kjv','book':b,'chapter':c,'verse':v}, {'status':'original_kjv','evidence':'Direct reference'})] if get(db,'kjv',b,c,v) else []
 if target=='russyn':
  q='''SELECT s.book,s.chapter,s.verse,s.part,k.part AS kjv_part,r.status,r.evidence,r.map_id FROM member k JOIN relation r ON r.id=k.relation_id JOIN member s ON s.relation_id=r.id AND s.translation='russyn' WHERE k.translation='kjv' AND k.book=? AND k.chapter=? AND k.verse=?'''
  return [({'translation':target,'book':x['book'],'chapter':x['chapter'],'verse':x['verse']},dict(x)) for x in db.execute(q,(b,c,v))]
 q='''SELECT source,book,chapter,verse,kjv_part,status,evidence FROM mapping WHERE source=? AND kjv_book=? AND kjv_chapter=? AND kjv_verse=?'''
 return [({'translation':target,'book':x['book'],'chapter':x['chapter'],'verse':x['verse']},dict(x)) for x in db.execute(q,(target,b,c,v))]

def compare(db,source,book,chapter,number,targetlangs,tokens=False):
 selected=get(db,source,book,chapter,number,tokens)
 if not selected:raise ValueError('Source verse not found in selected edition')
 aa=anchors(db,source,book,chapter,number);results=[]
 for target in targetlangs:
  if target==source:
   results.append({'verse':selected,'paths':[{'status':'identical_source'}]});continue
  seen={}
  for a in aa:
   for coord,edge in targets(db,target,a):
    # The edition-specific 3 John mapping uses equivalent, explicitly checked
    # KJV part labels in both datasets. Do not join disjoint verse parts.
    if (a['book'],a['chapter'],a['verse'])==('3JN',1,14):
     partmap={'a':'opening','b':'closing','opening':'opening','closing':'closing'}
     srcpart=partmap.get(a.get('part'));destpart=partmap.get(edge.get('kjv_part'))
     if srcpart and destpart and srcpart!=destpart:continue
    key=(coord['book'],coord['chapter'],coord['verse']);row=get(db,target,*key,tokens)
    if not row:continue
    path={'via_kjv':a,'target_link':edge}
    if key not in seen:seen[key]={'verse':row,'paths':[]}
    seen[key]['paths'].append(path)
  results.extend(seen.values())
 return {'selected':selected,'results':results,'kjv_anchors':aa,'missing_targets':[x for x in targetlangs if x!=source and not any(r['verse']['translation']==x for r in results)],'warning':'Reference candidates via KJV; source and target links may be unverified, partial, or include headings. No word-level alignment or semantic identity is implied.'}

def literal(db,lang,q,limit,offset):
 if not q.strip() or not 1<=limit<=100 or offset<0:raise ValueError('Invalid query, limit or offset')
 table,col=('location','translation') if lang in ('russyn','kjv') else ('verse','source')
 # For older texts fold the source at query time only when accents need removal;
 # the original index already stores diacritic-free folded text.
 folded=q.casefold() if table=='location' else fold(q)
 count=db.execute(f'SELECT count(*) FROM {table} WHERE {col}=? AND verse>0 AND instr(folded,?)>0',(lang,folded)).fetchone()[0]
 rows=[dict(x) for x in db.execute(f'SELECT {col} AS translation,book,chapter,verse,text FROM {table} WHERE {col}=? AND verse>0 AND instr(folded,?)>0 ORDER BY rowid LIMIT ? OFFSET ?',(lang,folded,limit,offset))]
 return {'query':q,'translation':lang,'total':count,'offset':offset,'results':rows,'method':'literal substring; source spelling and inflections affect results'}

def topics(db,terms,limit):
 if not terms or not 1<=limit<=100:raise ValueError('Provide terms and limit 1–100')
 rank=defaultdict(float);hits=defaultdict(set);passages={}
 for lang,term in dict.fromkeys(terms):
  t=term.strip().casefold()
  if not re.fullmatch(r'[^\W_]{3,40}',t,re.UNICODE):raise ValueError(f'Invalid search term: {term}')
  expr='"'+t+'"*'
  rows=db.execute('''SELECT p.*,bm25(multilang_fts) AS score FROM multilang_fts JOIN multilang_passage p ON p.id=multilang_fts.rowid WHERE multilang_fts MATCH ? AND p.translation=? ORDER BY score,p.id LIMIT 150''',(expr,lang)).fetchall()
  for i,row in enumerate(rows):rank[row['id']]+=1/(61+i);hits[row['id']].add(term);passages[row['id']]=dict(row)
 out=[]
 for id in sorted(rank,key=lambda x:(-rank[x],x))[:limit]:
  p=passages[id];p.pop('score',None);p['matched_terms']=sorted(hits[id]);out.append(p)
 return {'method':'lexical prefixes and rank fusion, not semantic or vector search','warning':'Candidates require context checking; results are not exhaustive. Input terms are not translated automatically.','results':out}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True,type=Path);sub=p.add_subparsers(dest='action',required=True)
 c=sub.add_parser('compare');c.add_argument('--from',dest='source',choices=LANGS,required=True);c.add_argument('--book',required=True);c.add_argument('--chapter',required=True,type=int);c.add_argument('--verse',required=True,type=int);c.add_argument('--to',action='append',choices=LANGS);c.add_argument('--tokens',action='store_true')
 s=sub.add_parser('search');s.add_argument('--translation',required=True,choices=LANGS);s.add_argument('query');s.add_argument('--limit',type=int,default=20);s.add_argument('--offset',type=int,default=0)
 t=sub.add_parser('topic');t.add_argument('--ru-term',action='append',default=[]);t.add_argument('--en-term',action='append',default=[]);t.add_argument('--nl-term',action='append',default=[]);t.add_argument('--limit',type=int,default=30)
 a=p.parse_args()
 with connect(a.database) as db:
  if a.action=='compare':r=compare(db,a.source,bookcode(a.book),a.chapter,a.verse,a.to or list(LANGS),a.tokens)
  elif a.action=='search':r=literal(db,a.translation,a.query,a.limit,a.offset)
  else:r=topics(db,[*(('russyn',x) for x in a.ru_term),*(('kjv',x) for x in a.en_term),*(('nld1917',x) for x in a.nl_term)],a.limit)
 print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
