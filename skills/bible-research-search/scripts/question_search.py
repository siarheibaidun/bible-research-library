#!/usr/bin/env python3
"""Retrieve Russian Bible passage candidates from AI-selected search concepts."""
import argparse,json,re,sqlite3,sys
from collections import defaultdict
from pathlib import Path
from lookup_verse import RUSSIAN_NAMES,NAMES
EXPECTED='9af20fe73fff9370acc8fd03cc0ffa718e1cf107d83fc401d41dcadc6c4e4a88'


def search(dbpath, terms, limit=30):
    if not dbpath.is_file(): raise ValueError('Passage index not found.')
    if not terms: raise ValueError('At least one meaningful term is required.')
    if not 1<=limit<=100: raise ValueError('Limit must be 1–100.')
    db=sqlite3.connect(f'{dbpath.resolve().as_uri()}?mode=ro',uri=True);db.row_factory=sqlite3.Row
    try:
        meta=dict(db.execute('SELECT key,value FROM metadata'))
        if meta.get('source_sha256')!=EXPECTED: raise ValueError('Unexpected Russian source edition.')
        rank=defaultdict(float); found=defaultdict(set); passages={}
        for term in dict.fromkeys(t.strip().casefold() for t in terms):
            if not re.fullmatch(r'[а-яёa-z0-9]{3,40}',term):
                raise ValueError(f'Terms must be individual letters/digits, at least 3 characters: {term!r}')
            # Treat every term as a literal prefix, not executable FTS syntax.
            expr='"'+term+'"*'
            rows=db.execute('SELECT p.*,bm25(passage_fts) AS score FROM passage_fts JOIN passage p ON p.id=passage_fts.rowid WHERE passage_fts MATCH ? ORDER BY score,p.id LIMIT 150',(expr,)).fetchall()
            for i,row in enumerate(rows):
                rank[row['id']]+=1/(60+i+1);found[row['id']].add(term);passages[row['id']]=dict(row)
        order=sorted(rank,key=lambda i:(-rank[i],i))[:limit];results=[]
        for i in order:
            p=passages[i];p.pop('score',None);p['matched_terms']=sorted(found[i]);p['candidate_rank_score']=round(rank[i],6)
            p['reference']=f"{RUSSIAN_NAMES.get(p['book'],NAMES[p['book']])} {p['chapter']}:{p['start']}–{p['end']}";results.append(p)
        return {'method':'lexical prefix retrieval of model-provided concepts, rank fusion; not vector embeddings',
                'warning':'Candidates require contextual relevance assessment. Results and rankings are not exhaustive.',
                'terms':terms,'results':results,'metadata':meta}
    finally:db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--term',action='append',required=True);p.add_argument('--limit',type=int,default=30);a=p.parse_args()
    try:print(json.dumps(search(a.database,a.term,a.limit),ensure_ascii=False,indent=2))
    except (ValueError,OSError,sqlite3.Error) as e:print(f'Error: {e}',file=sys.stderr);return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
