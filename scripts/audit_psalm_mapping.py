#!/usr/bin/env python3
"""Generate review-only Psalm mapping candidates from a pinned CrossWire source."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

CROSSWIRE_SHA256 = '76385bbd47834482c651e509e898d704cf27b5d4037ecff26ec7baf45f1edba6'
RUSSIAN_SHA256 = '9af20fe73fff9370acc8fd03cc0ffa718e1cf107d83fc401d41dcadc6c4e4a88'
KJV_SHA256 = '069646cd8722f6d57750d3b35d378181f9446dc3abeb81a554fd51b57c928689'
REF = r'Ps\.(\d+)\.(\d+)(?:!([a-z]))?'
EXPR = re.compile(r'^' + REF + r'(?:-' + REF + r')?$')


def parse_expression(expr):
    match = EXPR.fullmatch(expr.strip())
    if not match:
        raise ValueError('unsupported expression')
    c1, v1, part1, c2, v2, part2 = match.groups()
    c1, v1 = int(c1), int(v1)
    if c2 is None:
        return [{'chapter': c1, 'verse': v1, 'part': part1}]
    c2, v2 = int(c2), int(v2)
    if c1 != c2 or v1 > v2 or part1 or part2:
        raise ValueError('cross-chapter, reverse, or partial range requires review')
    return [{'chapter': c1, 'verse': i, 'part': None} for i in range(v1, v2 + 1)]


def parse_rule(line):
    if line.count('=') != 1:
        raise ValueError('invalid assignment')
    left, right = line.split('=')
    source, target = parse_expression(left), parse_expression(right)
    if len(source) == len(target):
        return [(s, [t]) for s, t in zip(source, target)]
    if len(source) == 1:
        return [(source[0], target)]
    if len(target) == 1:
        return [(s, target) for s in source]
    raise ValueError('unequal ranges require review')


def read_dataset(path, expected):
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('archive_sha256') != expected:
        raise ValueError(f'{path}: source archive checksum differs from expected edition')
    book = json.loads((path / 'PSA.json').read_text(encoding='utf-8'))
    if book.get('book') != 'PSA':
        raise ValueError(f'{path}: PSA.json has the wrong book ID')
    verses = {}
    for verse in book['verses']:
        key = (verse['chapter'], verse['verse'])
        if key in verses:
            raise ValueError(f'{path}: duplicate Psalm reference {key}')
        verses[key] = verse
    preambles = {item['chapter']: item['raw_usfm'] for item in book.get('chapter_preambles', [])}
    return verses, preambles


def audit(properties, russian_path, kjv_path):
    raw = properties.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CROSSWIRE_SHA256:
        raise ValueError('CrossWire source checksum does not match the pinned revision')
    ru, _ = read_dataset(russian_path, RUSSIAN_SHA256)
    kjv, headings = read_dataset(kjv_path, KJV_SHA256)
    candidates, issues, blocked = {}, [], {}
    for lineno, line in enumerate(raw.decode('utf-8-sig').splitlines(), start=1):
        line = line.strip()
        if not line.startswith('Ps.'):
            continue
        try:
            pairs = parse_rule(line)
        except ValueError as exc:
            issue = {'line': lineno, 'rule': line, 'reason': str(exc)}
            issues.append(issue)
            try:
                affected = parse_expression(line.split('=', 1)[0])
                for ref in affected:
                    blocked.setdefault((ref['chapter'], ref['verse']), []).append(issue)
            except ValueError:
                # A source expression we cannot enumerate makes no coverage claim.
                pass
            continue
        for source, targets in pairs:
            key = (source['chapter'], source['verse'])
            candidates.setdefault(key, []).append({'line': lineno, 'rule': line, 'source_part': source['part'], 'targets': targets})
    rows = []
    for (chapter, verse), source in sorted(ru.items()):
        entries = candidates.get((chapter, verse), [])
        row = {'russyn': {'book': 'PSA', 'chapter': chapter, 'verse': verse, 'text': source['text']}, 'candidates': entries}
        if (chapter, verse) in blocked:
            row['status'] = 'unparsed_rule_review'
            row['unparsed_rules'] = blocked[(chapter, verse)]
        elif not entries:
            row['status'] = 'no_explicit_rule'
        elif len(entries) != 1:
            row['status'] = 'overlapping_rules_review'
        else:
            entry = entries[0]
            target_output = []
            for target in entry['targets']:
                c, v, part = target['chapter'], target['verse'], target['part']
                if v == 0:
                    target_output.append({**target, 'kind': 'heading', 'source_usfm': headings.get(c)})
                else:
                    data = kjv.get((c, v))
                    target_output.append({**target, 'kind': 'verse', 'text': data['text'] if data else None})
            row['target_details'] = target_output
            if entry['source_part'] or any(t['verse'] == 0 or t['part'] for t in entry['targets']):
                row['status'] = 'heading_or_part_review'
            elif any(t['text'] is None for t in target_output):
                row['status'] = 'target_missing_review'
            elif len(entry['targets']) != 1:
                row['status'] = 'multiple_targets_review'
            else:
                row['status'] = 'candidate_text_review'
        rows.append(row)
    unused = [{'chapter': c, 'verse': v, 'rules': e} for (c, v), e in sorted(candidates.items()) if (c, v) not in ru]
    # Reverse coverage is informational: existence of a candidate never establishes equivalence.
    reverse = {}
    for source_key, entries in candidates.items():
        if source_key not in ru:
            continue
        for entry in entries:
            for target in entry['targets']:
                target_key = (target['chapter'], target['verse'])
                if target['verse'] > 0 and target_key in kjv:
                    reverse.setdefault(target_key, set()).add(source_key)
    reverse_summary = {'kjv_verse_count': len(kjv), 'with_parsed_candidate': len(reverse),
                       'without_parsed_candidate': len(set(kjv) - set(reverse)),
                       'with_multiple_source_candidates': sum(len(sources) > 1 for sources in reverse.values())}
    counts = {}
    for row in rows:
        counts[row['status']] = counts.get(row['status'], 0) + 1
    return {'status': 'review_only', 'source': {'url': 'https://github.com/crosswire/jsword/blob/a2c51f3c3a55416f3c991a67ef3d635c7ee55330/src/main/resources/org/crosswire/jsword/versification/Synodal.properties',
                'sha256': CROSSWIRE_SHA256, 'license': 'LGPL-2.1-or-later; see original source'},
            'dataset_archive_sha256': {'russyn': RUSSIAN_SHA256, 'kjv': KJV_SHA256},
            'limitations': ['Candidates are not verified mappings.', 'No equal-reference fallback is applied.',
                            'Zero refers to upstream heading notation; actual source locations require review.',
                            'Manifest hashes identify the declared archives, not the generated files.'],
            'counts': counts, 'reverse_coverage': reverse_summary, 'unparsed_rules': issues, 'source_references_not_in_dataset': unused, 'rows': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crosswire', required=True, type=Path, help='Pinned Synodal.properties')
    parser.add_argument('--russyn-data', type=Path, default=Path('output/russyn'))
    parser.add_argument('--kjv-data', type=Path, default=Path('output/kjv'))
    parser.add_argument('--output', type=Path, default=Path('output/psalm_mapping_review.json'))
    args = parser.parse_args()
    try:
        report = audit(args.crosswire, args.russyn_data, args.kjv_data)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print('Review-only report: ' + str(args.output))
        for status, count in sorted(report['counts'].items()):
            print(f'  {status}: {count}')
        print(f"  unparsed rules: {len(report['unparsed_rules'])}; source references absent: {len(report['source_references_not_in_dataset'])}")
        print(f"  KJV verses with / without parsed candidates: {report['reverse_coverage']['with_parsed_candidate']} / {report['reverse_coverage']['without_parsed_candidate']}")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
