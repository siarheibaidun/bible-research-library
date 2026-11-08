#!/usr/bin/env python3
"""Generate explicitly qualified, structurally checked Psalm source mappings."""
import argparse
from collections import Counter
import hashlib
import json
import sys
from pathlib import Path
from audit_psalm_mapping import audit, CROSSWIRE_SHA256, RUSSIAN_SHA256, KJV_SHA256

PILOT = Path(__file__).resolve().parents[1] / 'data' / 'versification' / 'russyn_kjv_pilot.json'


def reference(book, chapter, verse):
    return {'book': book, 'chapter': chapter, 'verse': verse}


def key(ref):
    return (ref['book'], ref['chapter'], ref['verse'])


def build(properties, ru, kjv, pilot_path=PILOT):
    report = audit(properties, ru, kjv)
    pilot = json.loads(pilot_path.read_text(encoding='utf-8'))
    for name, digest in [('russyn', RUSSIAN_SHA256), ('kjv', KJV_SHA256)]:
        if pilot['sources'][name]['archive_sha256'] != digest:
            raise ValueError(f'Pilot {name} source checksum does not match audit')
    # Every target referenced by any candidate is counted, including headings and
    # split relationships; a many-to-one target is not silently treated as 1:1.
    targets = Counter()
    for row in report['rows']:
        for entry in row['candidates']:
            for target in entry['targets']:
                if target['verse'] > 0:
                    targets[(target['chapter'], target['verse'])] += 1
    pilot_ru = {key(x) for rel in pilot['relationships'] for x in rel['russyn']}
    pilot_kjv = {key(x) for rel in pilot['relationships'] for x in rel['kjv']}
    mapping, exclusions = [], Counter()
    for row in report['rows']:
        ref = row['russyn']
        src = reference('PSA', ref['chapter'], ref['verse'])
        if key(src) in pilot_ru:
            exclusions['reserved_for_checked_pilot'] += 1
            continue
        status = row['status']
        if status != 'candidate_text_review':
            exclusions[status] += 1
            continue
        candidate = row['target_details'][0]
        dst = reference('PSA', candidate['chapter'], candidate['verse'])
        if key(dst) in pilot_kjv:
            exclusions['reserved_for_checked_pilot'] += 1
            continue
        if targets[(candidate['chapter'], candidate['verse'])] != 1:
            exclusions['target_multiple_rules_review'] += 1
            continue
        evidence = row['candidates'][0]
        mapping.append({'russyn': [src], 'kjv': [dst], 'status': 'source_mapped',
                        'source_rule': evidence['rule'], 'source_line': evidence['line']})
    result = {'mapping_id': 'crosswire-psalms-structural-v1', 'kind': 'source_mapped_candidates',
              'verification': 'Structurally checked against these datasets; text equivalence not individually verified.',
              'sources': {'russyn': {'archive_sha256': RUSSIAN_SHA256}, 'kjv': {'archive_sha256': KJV_SHA256}},
              'evidence': {'name': 'CrossWire JSword Synodal-to-KJV mapping', 'sha256': CROSSWIRE_SHA256,
                           'revision': 'a2c51f3c3a55416f3c991a67ef3d635c7ee55330',
                           'url': report['source']['url'], 'license': report['source']['license']},
              'pilot_sha256': hashlib.sha256(pilot_path.read_bytes()).hexdigest(), 'relationships': mapping}
    summary = {'source_verses': len(report['rows']), 'source_mapped': len(mapping),
               'excluded_for_review': dict(sorted(exclusions.items())),
               'unparsed_rules': report['unparsed_rules'],
               'source_references_not_in_dataset': report['source_references_not_in_dataset'],
               'reverse_coverage': report['reverse_coverage'],
               'caution': 'Source mappings describe candidate correspondences; text equivalence is not independently verified.'}
    return result, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crosswire', type=Path, required=True)
    parser.add_argument('--russyn-data', type=Path, default=Path('output/russyn'))
    parser.add_argument('--kjv-data', type=Path, default=Path('output/kjv'))
    parser.add_argument('--output', type=Path, default=Path('output/psalms_source_map.json'))
    parser.add_argument('--summary', type=Path, default=Path('output/psalms_source_summary.json'))
    args = parser.parse_args()
    try:
        if args.output.resolve() == args.summary.resolve():
            raise ValueError('Mapping and summary output must be different files.')
        mapping, summary = build(args.crosswire, args.russyn_data, args.kjv_data)
        for path, value in [(args.output, mapping), (args.summary, summary)]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f"Source-mapped candidates: {summary['source_mapped']} / {summary['source_verses']}")
        print('Excluded from source-mapped output (pilot entries are already text-checked):')
        for reason, count in summary['excluded_for_review'].items():
            print(f'  {reason}: {count}')
        if summary['unparsed_rules']:
            print('Unparsed source rules requiring investigation:')
            for issue in summary['unparsed_rules']:
                print(f"  line {issue['line']}: {issue['rule']} ({issue['reason']})")
        print(f'Mapping: {args.output}\nSummary: {args.summary}')
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
