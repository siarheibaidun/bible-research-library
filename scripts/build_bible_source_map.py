#!/usr/bin/env python3
"""Build source-attributed Russian–KJV candidates for all non-Psalm books."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import re
import sys
from pathlib import Path
from audit_psalm_mapping import CROSSWIRE_SHA256, RUSSIAN_SHA256, KJV_SHA256
from import_web_archive import BOOKS

PILOT = Path(__file__).resolve().parents[1] / 'data/versification/russyn_kjv_pilot.json'
OSIS = {'Num':'NUM', 'Josh':'JOS', '1Sam':'1SA', '1Kgs':'1KI', 'Job':'JOB', 'Eccl':'ECC',
        'Song':'SNG', 'Isa':'ISA', 'Dan':'DAN', 'Hos':'HOS', 'Jonah':'JON', 'Rom':'ROM', '2Cor':'2CO'}
REF = r'([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)(?:!([A-Za-z0-9]+))?'
EXPR = re.compile(r'^' + REF + r'(?:-' + REF + r')?$')


def key(r):
    return r['book'], r['chapter'], r['verse']


def ref(book, chapter, verse, part=None):
    r = {'book': book, 'chapter': chapter, 'verse': verse}
    if part: r['part'] = part
    return r


def load_index(directory, expected):
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('archive_sha256') != expected:
        raise ValueError(f'{directory}: source archive checksum mismatch')
    index = {}
    for code in BOOKS:
        if code == 'PSA': continue
        book = json.loads((directory/f'{code}.json').read_text(encoding='utf-8'))
        if book.get('book') != code: raise ValueError(f'{directory}: unexpected book ID in {code}.json')
        keys = [(v['chapter'], v['verse']) for v in book['verses']]
        if len(keys) != len(set(keys)): raise ValueError(f'{directory}: duplicate verses in {code}')
        index[code] = keys
    return index


def expand(expression, index):
    m = EXPR.fullmatch(expression.strip())
    if not m: raise ValueError('unsupported source syntax')
    b1,c1,v1,p1,b2,c2,v2,p2 = m.groups()
    if b1 not in OSIS or (b2 and b2 != b1): raise ValueError('unsupported or cross-book range')
    book=OSIS[b1]; c1=int(c1); v1=int(v1)
    if not b2: return [ref(book,c1,v1,p1)]
    c2=int(c2);v2=int(v2)
    sequence = list(index[book])
    # A virtual source heading in Song 1:0 is not a numbered source verse.
    for coordinate in ((c1,v1),(c2,v2)):
        if coordinate[1] == 0 and coordinate not in sequence: sequence.append(coordinate)
    sequence.sort()
    try: i=sequence.index((c1,v1)); j=sequence.index((c2,v2))
    except ValueError as exc: raise ValueError('range endpoint absent from dataset') from exc
    if i>j: raise ValueError('reverse range')
    out=[ref(book,c,v) for c,v in sequence[i:j+1]]
    if p1: out[0]['part']=p1
    if p2: out[-1]['part']=p2
    return out


def build(properties, russian_dir, kjv_dir):
    raw=properties.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CROSSWIRE_SHA256: raise ValueError('CrossWire source checksum mismatch')
    ru=load_index(russian_dir,RUSSIAN_SHA256); en=load_index(kjv_dir,KJV_SHA256)
    explicit=defaultdict(list); unresolved_rules=[]; absent_rules=[]
    for lineno,line in enumerate(raw.decode('utf-8-sig').splitlines(),1):
        line=line.strip()
        if not line or line.startswith(('#','!','Ps.')): continue
        if '=' not in line: continue
        left,right=line.split('=',1)
        try:
            if right.startswith('?'):
                # In these supplied archives Daniel 3:34–100 is absent.
                m=EXPR.fullmatch(left)
                if not m or m.group(1) != 'Dan' or (int(m.group(2)),int(m.group(3)),int(m.group(6)),int(m.group(7))) != (3,34,3,100):
                    raise ValueError('unsupported absent-section rule')
                present=[(c,v) for c,v in ru['DAN'] if c==3 and 34<=v<=100]
                if present: raise ValueError('absent-section source verses exist in edition')
                absent_rules.append({'line':lineno,'rule':line,'status':'source_verses_absent_in_this_edition'})
                continue
            source=expand(left,ru); target=expand(right,en)
            if len(source)==len(target): pairs=[(s,[t]) for s,t in zip(source,target)]
            elif len(source)==1: pairs=[(source[0],target)]
            elif len(target)==1: pairs=[(s,target) for s in source]
            else: raise ValueError(f'unsupported cardinality {len(source)}:{len(target)}')
            for src,dst in pairs:
                if src['verse']==0: # title not represented as a numbered verse
                    absent_rules.append({'line':lineno,'rule':line,'status':'source_heading_not_a_numbered_verse','targets':dst});continue
                if key(src) not in {(src['book'],c,v) for c,v in ru[src['book']]}:
                    raise ValueError('explicit source verse missing')
                explicit[key(src)].append({'targets':dst,'line':lineno,'rule':line})
        except ValueError as exc:
            unresolved_rules.append({'line':lineno,'rule':line,'reason':str(exc)})
    if unresolved_rules:
        # Do not generate misleading implicit matches around unsupported rules.
        raise ValueError('Unparsed rules: '+json.dumps(unresolved_rules,ensure_ascii=False))
    # Edition-specific checks: some upstream rules omit parts of a source verse.
    corrections={('1SA',20,42): [ref('1SA',20,42,'a')],
                 ('1SA',20,43): [ref('1SA',20,42,'b')],
                 ('2CO',11,32): [ref('2CO',11,32),ref('2CO',11,33)],
                 ('2CO',13,12): [ref('2CO',13,12),ref('2CO',13,13)],
                 ('LEV',14,55): [ref('LEV',14,55),ref('LEV',14,56)],
                 ('LEV',14,56): [ref('LEV',14,57)],
                 ('ACT',19,40): [ref('ACT',19,40),ref('ACT',19,41)],
                 ('3JN',1,14): [ref('3JN',1,14,'a')],
                 ('3JN',1,15): [ref('3JN',1,14,'b')]}
    # Russian Proverbs 13:14 has no established KJV verse counterpart; the
    # remaining Russian verses in that chapter are offset by one.
    for verse in range(15,27):
        corrections[('PRO',13,verse)] = [ref('PRO',13,verse-1)]
    source_only={('JOS',24,34),('JOS',24,35),('JOS',24,36),
                 ('PRO',4,28),('PRO',4,29),('PRO',13,14)}
    pilot=json.loads(PILOT.read_text(encoding='utf-8'))
    for lang, expected in [('russyn',RUSSIAN_SHA256),('kjv',KJV_SHA256)]:
        if pilot['sources'][lang]['archive_sha256'] != expected: raise ValueError('Pilot archive mismatch')
    pilot_index={key(x):r for r in pilot['relationships'] for x in r['russyn'] if x['book']!='PSA'}
    rels=[]; unresolved=[]
    for book in BOOKS:
        if book=='PSA': continue
        target_set=set(en[book])
        for chapter,verse in ru[book]:
            k=(book,chapter,verse); source=ref(book,chapter,verse)
            if k in source_only:
                targets=[];status='no_numbered_counterpart';evidence='No direct numbered KJV counterpart established in the corresponding book.'
            elif k in pilot_index:
                pair=pilot_index[k]; targets=pair['kjv']; status='text_checked_pilot'; evidence='Previously text-checked pilot.'
            elif k in corrections:
                targets=corrections[k];status='edition_override';evidence='Edition-specific correspondence checked against both source texts; KJV verse parts, where marked, are shown in full.'
            elif len(explicit.get(k,[]))==1:
                candidate=explicit[k][0];targets=candidate['targets'];status='source_mapped';evidence={'line':candidate['line'],'rule':candidate['rule']}
            elif len(explicit.get(k,[]))>1:
                unresolved.append({'source':source,'reason':'overlapping_source_rules','rules':explicit[k]});continue
            elif (chapter,verse) in target_set:
                targets=[ref(book,chapter,verse)];status='implicit_same_reference';evidence='JSword same-reference fallback; no individual textual verification.'
            else:
                unresolved.append({'source':source,'reason':'no_explicit_rule_and_same_reference_missing'});continue
            missing=[t for t in targets if (t['chapter'],t['verse']) not in target_set]
            if missing:
                unresolved.append({'source':source,'reason':'target_missing','targets':missing});continue
            rels.append({'russyn':[source], 'kjv':targets, 'status':status,'evidence':evidence})
    target_counts=Counter(key(t) for r in rels for t in r['kjv'])
    allowed_shared={('1SA',20,42),('1KI',18,33),('3JN',1,14)}
    unexpected_shared=sorted(k for k,n in target_counts.items() if n>1 and k not in allowed_shared)
    if unexpected_shared:
        raise ValueError(f'Unexpected overlapping target references: {unexpected_shared}')
    covered=set(target_counts)
    missing_target=[ref(book,c,v) for book in BOOKS if book!='PSA' for c,v in en[book] if (book,c,v) not in covered]
    return {'mapping_id':'russyn-kjv-other-books-v1','kind':'bible_source_map',
            'verification':'Published-rule and same-reference candidates are not individually text-verified.',
            'sources':{'russyn':{'archive_sha256':RUSSIAN_SHA256},'kjv':{'archive_sha256':KJV_SHA256}},
            'evidence':{'name':'CrossWire JSword Synodal-to-KJV mapping','sha256':CROSSWIRE_SHA256,
                        'url':'https://github.com/crosswire/jsword/blob/a2c51f3c3a55416f3c991a67ef3d635c7ee55330/src/main/resources/org/crosswire/jsword/versification/Synodal.properties',
                        'license':'LGPL-2.1-or-later; see original source'},
            'pilot_sha256':hashlib.sha256(PILOT.read_bytes()).hexdigest(),
            'relationships':rels,'unresolved_sources':unresolved,'uncovered_kjv':missing_target,
            'excluded_source_rules':absent_rules,'counts':{'russian_numbered':sum(map(len,ru.values())),
                'kjv_numbered':sum(map(len,en.values())), 'relationships':len(rels),
                'status':dict(Counter(r['status'] for r in rels))}}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--crosswire',type=Path,required=True)
    p.add_argument('--russyn-data',type=Path,default=Path('output/russyn'));p.add_argument('--kjv-data',type=Path,default=Path('output/kjv'))
    p.add_argument('--output',type=Path,default=Path('output/bible_other_books_map.json'));a=p.parse_args()
    try:
        result=build(a.crosswire,a.russyn_data,a.kjv_data);a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f"Processed {result['counts']['relationships']} of {result['counts']['russian_numbered']} Russian verse records.")
        print(f"Records without an established numbered KJV counterpart: {result['counts']['status'].get('no_numbered_counterpart',0)}.")
        print(f"Unresolved Russian records: {len(result['unresolved_sources'])}; KJV records without target: {len(result['uncovered_kjv'])}.")
        print('Published-rule and same-reference candidates have not been individually text-verified.')
        print(f'Map: {a.output}')
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:
        print(f'Error: {exc}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
