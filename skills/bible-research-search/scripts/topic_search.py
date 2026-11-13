#!/usr/bin/env python3
"""Experimental parent–child thematic retrieval over the local Bible index."""
import argparse
import json
import sys
from pathlib import Path
from search import open_db, fmt_ref

CATALOG = Path(__file__).resolve().parents[1] / 'references' / 'parents-children.json'


def retrieve(db, lang, limit, include_candidates):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    curated=[]; covered=set()
    for entry in catalog['passages'][:limit]:
        rows=db.execute('SELECT book,chapter,verse,text FROM location WHERE translation=? AND book=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse',
                        (lang,entry['book'],entry['chapter'],entry['start'],entry['end'])).fetchall()
        if [r['verse'] for r in rows] != list(range(entry['start'],entry['end']+1)):
            raise ValueError(f"Missing or unexpected verses: {entry['book']} {entry['chapter']}:{entry['start']}-{entry['end']}")
        verses=[{'reference':fmt_ref(lang,r['book'],r['chapter'],r['verse']),'text':r['text']} for r in rows]
        covered.update((r['book'],r['chapter'],r['verse']) for r in rows)
        curated.append({'category':entry['category'],'reason':entry['reason'],'verses':verses})
    result={'topic':catalog['topic'],'translation':lang,'method':'curated theme examples; not semantic vector search',
            'warning':'Selection is experimental and not an exhaustive list of all relevant passages.',
            'curated_total':len(catalog['passages']),'curated_shown':len(curated),'passages':curated}
    if include_candidates:
        terms=catalog['search_terms'][lang];where=' OR '.join('instr(folded, ?) > 0' for _ in terms)
        rows=db.execute('SELECT book,chapter,verse,text FROM location WHERE translation=? AND verse>0 AND ('+where+')',(lang,*[x.casefold() for x in terms])).fetchall()
        rest=[r for r in rows if (r['book'],r['chapter'],r['verse']) not in covered]
        result['keyword_candidates']={'description':'Literal lexical matches only; not individually judged relevant and not an exhaustive conceptual search.',
          'terms':terms,'total':len(rest),'shown':min(len(rest),20),'items':[{'reference':fmt_ref(lang,r['book'],r['chapter'],r['verse']),'text':r['text']} for r in rest[:20]]}
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True,type=Path)
    p.add_argument('--translation',choices=['russyn','kjv'],default='russyn');p.add_argument('--limit',type=int,default=15)
    p.add_argument('--candidates',action='store_true');a=p.parse_args()
    try:
        if not 1<=a.limit<=15:raise ValueError('Limit must be between 1 and 15.')
        db,meta=open_db(a.database)
        try:out=retrieve(db,a.translation,a.limit,a.candidates)
        finally:db.close()
        out['provenance']=meta;print(json.dumps(out,ensure_ascii=False,indent=2))
    except (ValueError,OSError,KeyError) as e:print(f'Error: {e}',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
