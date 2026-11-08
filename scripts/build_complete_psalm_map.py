#!/usr/bin/env python3
"""Build source-attributed Psalm correspondences, retaining heading/part scope."""
import argparse
import json
import re
import sys
from pathlib import Path
from audit_psalm_mapping import audit, CROSSWIRE_SHA256, RUSSIAN_SHA256, KJV_SHA256

PILOT = Path(__file__).resolve().parents[1] / 'data/versification/russyn_kjv_pilot.json'


def ref(c, v, part=None):
    value = {'book': 'PSA', 'chapter': c, 'verse': v}
    if part:
        value['part'] = part
    return value


def build(properties, ru, kjv):
    report = audit(properties, ru, kjv)
    pilot = json.loads(PILOT.read_text(encoding='utf-8'))
    for lang, digest in [('russyn', RUSSIAN_SHA256), ('kjv', KJV_SHA256)]:
        if pilot['sources'][lang]['archive_sha256'] != digest:
            raise ValueError('Pilot and datasets do not identify the same archives.')
    psalm_pilot = {(r['chapter'], r['verse']): item for item in pilot['relationships'] for r in item['russyn'] if r['book'] == 'PSA'}
    kjv_ps = json.loads((kjv / 'PSA.json').read_text(encoding='utf-8'))
    verse_set = {(v['chapter'], v['verse']) for v in kjv_ps['verses']}
    heading_set = {x['chapter'] for x in kjv_ps.get('chapter_preambles', []) if '\\d ' in x['raw_usfm']}
    rels, heading_rels, omissions = [], [], []
    ru_ps = json.loads((ru / 'PSA.json').read_text(encoding='utf-8'))
    ru_preambles = {x['chapter']: x['raw_usfm'] for x in ru_ps.get('chapter_preambles', [])}
    allowed_identity = {1, 2, 148, 149, 150}
    for row in report['rows']:
        c, v = row['russyn']['chapter'], row['russyn']['verse']
        src = ref(c, v); state = row['status']; evidence = None
        if (c, v) in psalm_pilot:
            dst = psalm_pilot[(c, v)]['kjv']; status = 'text_checked_pilot'; evidence = 'Text-checked pilot'
            if state == 'heading_or_part_review' and len(row.get('target_details', [])) == 2:
                target_heading = row['target_details'][0]
                if target_heading['verse'] == 0 and '\\d ' in ru_preambles.get(c, ''):
                    heading_rels.append({'russyn': [ref(c, 0)], 'kjv': [ref(target_heading['chapter'], 0)],
                                         'status': 'edition_adjusted_source_mapping',
                                         'evidence': {'rule': row['candidates'][0]['rule'],
                                                      'line': row['candidates'][0]['line'],
                                                      'adjustment': 'Both headings are chapter preamble content.'}})
        elif c == 89:
            # The Russian edition joins KJV 90:5–6 in its verse 6.
            if v == 1: dst = [ref(90, 0)]
            elif 2 <= v <= 5: dst = [ref(90, v-1)]
            elif v == 6: dst = [ref(90, 5), ref(90, 6)]
            else: dst = [ref(90, v)]
            status = 'edition_override'; evidence = 'Compared Psalm 89/90 source texts; verse 1 is heading, verse 6 spans KJV 5–6.'
        elif (c, v) == (86, 1):
            dst = [ref(87, 0)]; status = 'edition_override'; evidence = 'Russian verse is heading only.'
        elif (c, v) == (86, 2):
            dst = [ref(87, 1), ref(87, 2)]; status = 'edition_override'; evidence = 'Russian verse combines KJV 87:1–2.'
        elif state == 'no_explicit_rule' and c in allowed_identity:
            dst = [ref(c, v)]; status = 'text_checked_identity'; evidence = 'Equal-reference Psalm checked against both source editions.'
        elif state in ('candidate_text_review', 'heading_or_part_review', 'multiple_targets_review') and len(row.get('candidates', [])) == 1:
            e = row['candidates'][0]; dst = [ref(t['chapter'], t['verse'], t['part']) for t in e['targets']]
            status = 'source_mapped'; evidence = {'rule': e['rule'], 'line': e['line']}
            # A rule including KJV heading and verse can reflect a heading that
            # this Russian edition stores before verse 1. Preserve only the verse
            # in that case, except where the verse itself includes the heading.
            if len(dst) == 2 and dst[0]['verse'] == 0 and dst[1]['verse'] > 0 and (c, v) != (65, 1):
                head = dst[0]
                preamble = ru_preambles.get(c, '')
                if not ('\\d ' in preamble or (c == 72 and '\\m ' in preamble)):
                    omissions.append({'chapter': c, 'verse': v, 'reason': 'Russian preamble heading not found'}); continue
                heading_rels.append({'russyn': [ref(c, 0)], 'kjv': [head], 'status': 'edition_adjusted_source_mapping',
                                     'evidence': {'rule': e['rule'], 'line': e['line'],
                                                  'adjustment': 'Both headings are chapter preamble content.'}})
                dst = [dst[1]]; status = 'edition_adjusted_source_mapping'
                evidence['adjustment'] = 'Russian chapter preamble contains the heading; numbered verse maps to KJV numbered verse.'
        else:
            omissions.append({'chapter': c, 'verse': v, 'reason': state}); continue
        invalid = [t for t in dst if ((t['verse'] == 0 and t['chapter'] not in heading_set) or (t['verse'] > 0 and (t['chapter'], t['verse']) not in verse_set))]
        if invalid:
            omissions.append({'chapter': c, 'verse': v, 'reason': 'target_not_found', 'targets': invalid}); continue
        rels.append({'russyn': [src], 'kjv': dst, 'status': status, 'evidence': evidence})
    verse_count = len(rels)
    rels.extend(heading_rels)
    source_keys = [(x['chapter'], x['verse']) for rel in rels for x in rel['russyn']]
    if len(source_keys) != len(set(source_keys)):
        raise ValueError('A Russian source location appears in multiple relationships.')
    covered_kjv = {(x['chapter'], x['verse']) for rel in rels for x in rel['kjv']}
    missing_kjv_verses = sorted(verse_set - covered_kjv)
    missing_kjv_headings = sorted(heading_set - {c for c, v in covered_kjv if v == 0})
    if missing_kjv_verses or missing_kjv_headings:
        raise ValueError(f'Unmapped KJV locations: verses={missing_kjv_verses}; headings={missing_kjv_headings}')
    ru_headings = {c for c, raw in ru_preambles.items() if re.search(r'(?m)^\\(?:d|m)\s+\S', raw)}
    mapped_ru_headings = {c for c, v in source_keys if v == 0}
    unresolved_ru_headings = sorted(ru_headings - mapped_ru_headings)
    return {'mapping_id': 'russyn-kjv-psalms-v1', 'kind': 'complete_psalm_source_map',
            'verification': 'Source-mapped rules are not individually text-verified; heading parts are displayed in full.',
            'sources': {'russyn': {'archive_sha256': RUSSIAN_SHA256}, 'kjv': {'archive_sha256': KJV_SHA256}},
            'evidence': {'name': 'CrossWire JSword Synodal-to-KJV mapping', 'sha256': CROSSWIRE_SHA256,
                         'url': report['source']['url'], 'license': report['source']['license']},
            'relationships': rels, 'omissions': omissions, 'source_count': len(report['rows']), 'verse_relationship_count': verse_count, 'heading_relationship_count': len(heading_rels),
            'kjv_verses_covered': len(verse_set), 'kjv_headings_covered': len(heading_set),
            'unresolved_russian_headings': unresolved_ru_headings}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--crosswire', type=Path, required=True)
    p.add_argument('--russyn-data', type=Path, default=Path('output/russyn'))
    p.add_argument('--kjv-data', type=Path, default=Path('output/kjv'))
    p.add_argument('--output', type=Path, default=Path('output/psalms_complete_map.json'))
    a = p.parse_args()
    try:
        result = build(a.crosswire, a.russyn_data, a.kjv_data)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f"Mapped {result['verse_relationship_count']} of {result['source_count']} Russian Psalm verse records; {result['heading_relationship_count']} additional heading relationships.")
        print(f"KJV verses/headings covered: {result['kjv_verses_covered']} / {result['kjv_headings_covered']}.")
        print(f"Russian verse omissions: {len(result['omissions'])}; Russian preamble headings without an established counterpart: {len(result['unresolved_russian_headings'])}.")
        print('Source-mapped entries are not individually text-verified.')
        print(f'Map: {a.output}')
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
