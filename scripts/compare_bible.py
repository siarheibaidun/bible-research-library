#!/usr/bin/env python3
"""Compare non-Psalm Russian and KJV references using a generated source map."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from audit_psalm_mapping import CROSSWIRE_SHA256, RUSSIAN_SHA256, KJV_SHA256
from lookup_verse import NAMES, RUSSIAN_NAMES, parse_reference, read_note


def loc_key(x):
    return x['book'],x['chapter'],x['verse']


def load_book(directory, code):
    book=json.loads((directory/f'{code}.json').read_text(encoding='utf-8'))
    if book.get('book')!=code: raise ValueError(f'{directory}: incorrect book identifier for {code}')
    verses={}
    for verse in book['verses']:
        k=(verse['chapter'],verse['verse'])
        if k in verses: raise ValueError(f'{directory}: duplicate reference {code} {k}')
        verses[k]=verse
    return verses


def compare(reference, source, russian_dir, kjv_dir, mapping_file):
    if source not in ('russyn','kjv'): raise ValueError('Source must be russyn or kjv.')
    code,chapter,verse=parse_reference(reference)
    if code=='PSA': raise ValueError('Use the Psalms map for Psalm references.')
    mapping=json.loads(mapping_file.read_text(encoding='utf-8'))
    if mapping.get('kind')!='bible_source_map' or mapping.get('evidence',{}).get('sha256')!=CROSSWIRE_SHA256:
        raise ValueError('Unsupported Bible source map or provenance.')
    pilot = Path(__file__).resolve().parents[1] / 'data/versification/russyn_kjv_pilot.json'
    if mapping.get('pilot_sha256') != hashlib.sha256(pilot.read_bytes()).hexdigest():
        raise ValueError('Bible map was generated for a different pilot; regenerate it.')
    dirs={'russyn':russian_dir,'kjv':kjv_dir}; expected={'russyn':RUSSIAN_SHA256,'kjv':KJV_SHA256};books={};manifests={}
    for lang,path in dirs.items():
        if mapping['sources'][lang]['archive_sha256']!=expected[lang]:raise ValueError(f'{lang}: mapping checksum mismatch.')
        manifest=json.loads((path/'manifest.json').read_text(encoding='utf-8'))
        if manifest.get('archive_sha256')!=expected[lang]:raise ValueError(f'{lang}: dataset archive checksum mismatch.')
        manifests[lang]=manifest; books[lang]=load_book(path,code)
    query=(code,chapter,verse)
    hits=[r for r in mapping['relationships'] if any(loc_key(x)==query for x in r[source])]
    if not hits:
        if source=='kjv' and any(loc_key(x)==query for x in mapping.get('uncovered_kjv',[])):
            hits=[{'russyn':[],'kjv':[{'book':code,'chapter':chapter,'verse':verse}],
                   'status':'counterpart_unresolved','evidence':'No directly corresponding numbered Russian verse is established in this dataset.'}]
        else:raise ValueError(f'No mapped relationship for {reference}; no match was assumed.')
    return mapping,manifests,books,hits


def display(result):
    mapping,manifests,books,hits=result
    lines=[f"Mapping: {mapping['mapping_id']}", 'Status: '+', '.join(sorted({h['status'] for h in hits})),
           'Published-rule and same-reference matches have not been individually text-verified.']
    if len(hits)>1:lines.append('Multiple related portions are shown together.')
    for hit in hits:
        e=hit.get('evidence')
        if isinstance(e,dict):lines.append(f"Source rule (line {e.get('line','?')}): {e.get('rule','')}")
        elif e:lines.append(f'Evidence: {e}')
    for lang in ('russyn','kjv'):
        lines.append(f"\n{manifests[lang].get('edition',lang)}:")
        locations={}
        for hit in hits:
            for r in hit[lang]:
                k=loc_key(r);locations.setdefault(k,set())
                if r.get('part'):locations[k].add(r['part'])
        if not locations:lines.append('No directly corresponding numbered verse is established in this dataset.')
        for (book,chapter,verse),parts in locations.items():
            data=books[lang].get((chapter,verse))
            if data is None:raise ValueError(f'Mapped verse missing: {book} {chapter}:{verse}')
            title=RUSSIAN_NAMES.get(book,NAMES[book]) if lang=='russyn' else NAMES[book]
            lines.append(f"{title} {chapter}:{verse} — {data['text'] or '[No verse text in this source.]'}")
            if parts:lines.append('  Corresponding part(s) '+', '.join(sorted(parts))+'; full verse shown as context, exact boundaries not isolated.')
            for note in data.get('notes',[]):
                parsed=read_note(note['raw_usfm']);label='Footnote' if note.get('type')=='footnote' else 'Cross-reference'
                lines.append(f'  {label} ({parsed[0]}): {parsed[1]}' if parsed else f"  {label} (USFM): {note['raw_usfm']}")
        lines.append(f"Archive SHA-256: {manifests[lang]['archive_sha256']}")
    lines.append(f"\nMapping source: {mapping['evidence']['url']}")
    return '\n'.join(lines)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('reference');p.add_argument('--from',dest='source',required=True,choices=('russyn','kjv'))
    p.add_argument('--russyn-data',type=Path,default=Path('output/russyn'));p.add_argument('--kjv-data',type=Path,default=Path('output/kjv'))
    p.add_argument('--map',type=Path,default=Path('output/bible_other_books_map.json'));a=p.parse_args()
    try:print(display(compare(a.reference,a.source,a.russyn_data,a.kjv_data,a.map)))
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:print(f'Error: {exc}',file=sys.stderr);return 1
    return 0


if __name__=='__main__':raise SystemExit(main())
