#!/usr/bin/env python3
"""Compare Russian and KJV Psalms using an explicitly generated source map."""
import argparse
import json
import re
import sys
from pathlib import Path
from audit_psalm_mapping import CROSSWIRE_SHA256, RUSSIAN_SHA256, KJV_SHA256
from import_web_archive import render
from lookup_verse import ALIASES, normalize, read_note


def parse_ref(value):
    match = re.fullmatch(r'\s*(.+?)\s+(\d+):(\d+)\s*', value)
    if not match or ALIASES.get(normalize(match.group(1))) != 'PSA':
        raise ValueError('Use a Psalm reference such as "Псалом 3:1" or "Psalm 3:0" for a heading.')
    c, v = int(match.group(2)), int(match.group(3))
    if c < 1:
        raise ValueError('Psalm chapter must be positive.')
    return {'book': 'PSA', 'chapter': c, 'verse': v}


def same_location(a, b):
    return all(a.get(k) == b.get(k) for k in ('book', 'chapter', 'verse'))


def load_source(path, expected):
    manifest = json.loads((path / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('archive_sha256') != expected:
        raise ValueError(f'{path}: source archive checksum does not match the mapping.')
    book = json.loads((path / 'PSA.json').read_text(encoding='utf-8'))
    if book.get('book') != 'PSA':
        raise ValueError(f'{path}: invalid Psalm book identifier.')
    return manifest, book


def read_location(book, target):
    chapter, verse = target['chapter'], target['verse']
    if verse == 0:
        preambles = [p for p in book.get('chapter_preambles', []) if p['chapter'] == chapter]
        if len(preambles) != 1:
            raise ValueError(f'Heading for Psalm {chapter} not found uniquely.')
        segments = re.findall(r'(?m)^\\(?:d|m)\s+([^\r\n]+)', preambles[0]['raw_usfm'])
        if not segments:
            raise ValueError(f'Heading for Psalm {chapter} could not be interpreted.')
        texts, notes = [], []
        for segment in segments:
            text, part_notes, _ = render(segment, f'Psalm {chapter} heading')
            texts.append(text)
            notes.extend(part_notes)
        return ' '.join(texts), notes
    found = [x for x in book['verses'] if x['chapter'] == chapter and x['verse'] == verse]
    if len(found) != 1:
        raise ValueError(f'Psalm {chapter}:{verse} not found uniquely.')
    return found[0]['text'], found[0].get('notes', [])


def compare(reference, source, russian_dir, kjv_dir, mapping_file):
    if source not in ('russyn', 'kjv'):
        raise ValueError('Source must be russyn or kjv.')
    requested = parse_ref(reference)
    mapping = json.loads(mapping_file.read_text(encoding='utf-8'))
    if mapping.get('kind') != 'complete_psalm_source_map' or mapping.get('evidence', {}).get('sha256') != CROSSWIRE_SHA256:
        raise ValueError('Unsupported Psalm map or source provenance.')
    expected = {'russyn': RUSSIAN_SHA256, 'kjv': KJV_SHA256}
    paths = {'russyn': russian_dir, 'kjv': kjv_dir}
    sources = {}
    for name, path in paths.items():
        if mapping['sources'][name]['archive_sha256'] != expected[name]:
            raise ValueError(f'Mapping has an unexpected {name} source checksum.')
        sources[name] = load_source(path, expected[name])
    hits = [r for r in mapping['relationships'] if any(same_location(x, requested) for x in r[source])]
    if not hits:
        if source == 'russyn' and requested['verse'] == 0 and requested['chapter'] in mapping.get('unresolved_russian_headings', []):
            hits = [{'russyn': [requested], 'kjv': [], 'status': 'counterpart_unresolved',
                     'evidence': 'No KJV heading or verse correspondence has been established.'}]
        else:
            raise ValueError(f'No mapped relationship for {reference}; no match was assumed.')
    return mapping, sources, hits


def display(result):
    mapping, sources, hits = result
    statuses = sorted({hit['status'] for hit in hits})
    lines = [f"Mapping: {mapping['mapping_id']}", 'Status: ' + ', '.join(statuses),
             'Source-mapped relationships are not individually text-verified.']
    if len(hits) > 1:
        lines.append('Multiple related source portions are shown together.')
    for hit in hits:
        evidence = hit.get('evidence')
        if isinstance(evidence, dict):
            if 'rule' in evidence:
                lines.append(f"Source rule (line {evidence.get('line', '?')}): {evidence['rule']}")
            if evidence.get('adjustment'):
                lines.append(f"Edition adjustment: {evidence['adjustment']}")
        elif evidence:
            lines.append(f'Evidence: {evidence}')
    for name in ('russyn', 'kjv'):
        manifest, book = sources[name]
        lines.append(f"\n{manifest.get('edition', name)}:")
        locations = {}
        for hit in hits:
            for ref in hit[name]:
                key = (ref['chapter'], ref['verse'])
                locations.setdefault(key, set())
                if ref.get('part'):
                    locations[key].add(ref['part'])
        if not locations:
            lines.append('No established corresponding location in this edition.')
        for (chapter, verse), parts in locations.items():
            label = 'Псалтирь' if name == 'russyn' else 'Psalms'
            text, notes = read_location(book, {'chapter': chapter, 'verse': verse})
            loc = f'{chapter}:heading' if verse == 0 else f'{chapter}:{verse}'
            lines.append(f"{label} {loc} — {text or '[No verse text in this source.]'}")
            if parts:
                lines.append('  Mapping identifies heading part(s) ' + ', '.join(sorted(parts)) + '; full heading shown, part boundaries not isolated.')
            for note in notes:
                parsed = read_note(note['raw_usfm'])
                note_type = 'Footnote' if note.get('type') == 'footnote' else 'Cross-reference'
                lines.append(f'  {note_type} ({parsed[0]}): {parsed[1]}' if parsed else f"  {note_type} (USFM): {note['raw_usfm']}")
        lines.append(f"Archive SHA-256: {manifest['archive_sha256']}")
    lines.append(f"\nRule source: {mapping['evidence']['url']}")
    return '\n'.join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('reference')
    p.add_argument('--from', dest='source', required=True, choices=('russyn', 'kjv'))
    p.add_argument('--russyn-data', type=Path, default=Path('output/russyn'))
    p.add_argument('--kjv-data', type=Path, default=Path('output/kjv'))
    p.add_argument('--map', type=Path, default=Path('output/psalms_complete_map.json'))
    a = p.parse_args()
    try:
        print(display(compare(a.reference, a.source, a.russyn_data, a.kjv_data, a.map)))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr); return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
