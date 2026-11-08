#!/usr/bin/env python3
"""Compare only explicitly mapped verses between the two reviewed datasets."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from lookup_verse import NAMES, RUSSIAN_NAMES, parse_reference, read_note

DEFAULT_MAP = Path(__file__).resolve().parents[1] / 'data' / 'versification' / 'russyn_kjv_pilot.json'


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_dataset(path, expected):
    manifest = load_json(path / 'manifest.json')
    if manifest.get('archive_sha256') != expected:
        raise ValueError(f'{path}: dataset archive checksum does not match the mapping.')
    return manifest


def get_verse(path, ref):
    code = ref['book']
    if code not in NAMES:
        raise ValueError(f'Unsupported book in mapping: {code}')
    book = load_json(path / f'{code}.json')
    if book.get('book') != code:
        raise ValueError(f'{path}: incorrect book identifier in {code}.json.')
    found = [v for v in book['verses'] if (v['chapter'], v['verse']) == (ref['chapter'], ref['verse'])]
    if len(found) != 1:
        raise ValueError(f'{path}: mapped verse {code} {ref["chapter"]}:{ref["verse"]} missing or duplicated.')
    return found[0]


def compare(reference, source, russian_dir, kjv_dir, mapping_file=DEFAULT_MAP, source_map_file=None):
    code, chapter, verse = parse_reference(reference)
    ref = {'book': code, 'chapter': chapter, 'verse': verse}
    mapping = load_json(mapping_file)
    directories = {'russyn': russian_dir, 'kjv': kjv_dir}
    manifests = {key: validate_dataset(path, mapping['sources'][key]['archive_sha256']) for key, path in directories.items()}
    if source not in directories:
        raise ValueError('Source must be russyn or kjv.')
    matches = [entry for entry in mapping['relationships'] if ref in entry[source]]
    if not matches and source_map_file is not None:
        candidate_map = load_json(source_map_file)
        expected_source = '76385bbd47834482c651e509e898d704cf27b5d4037ecff26ec7baf45f1edba6'
        if candidate_map.get('kind') != 'source_mapped_candidates' or candidate_map.get('evidence', {}).get('sha256') != expected_source:
            raise ValueError('Unsupported source map or mapping provenance.')
        if candidate_map.get('pilot_sha256') != hashlib.sha256(mapping_file.read_bytes()).hexdigest():
            raise ValueError('Source map was generated for a different pilot; rebuild it.')
        for name, path in directories.items():
            validate_dataset(path, candidate_map['sources'][name]['archive_sha256'])
            if candidate_map['sources'][name]['archive_sha256'] != mapping['sources'][name]['archive_sha256']:
                raise ValueError(f'Source map and pilot disagree on {name} edition.')
        matches = [entry for entry in candidate_map['relationships'] if ref in entry[source]]
        if len(matches) == 1:
            match = matches[0]
            if match.get('status') != 'source_mapped' or len(match['russyn']) != 1 or len(match['kjv']) != 1:
                raise ValueError('Invalid source-mapped relationship.')
            mapping = dict(candidate_map)
            mapping['selected_evidence'] = {'source_rule': match['source_rule'], 'source_line': match['source_line']}
    if not matches:
        raise ValueError(f'No available mapping for {reference} in {source}; no automatic match was assumed.')
    if len(matches) != 1:
        raise ValueError(f'Ambiguous mapping for {reference} in {source}.')
    result = {}
    for key, path in directories.items():
        result[key] = [(r, get_verse(path, r)) for r in matches[0][key]]
    return mapping, manifests, result


def format_comparison(result):
    mapping, manifests, verses = result
    if mapping.get('kind') == 'source_mapped_candidates':
        evidence = mapping['evidence']
        selected = mapping['selected_evidence']
        lines = [f"Mapping: {mapping['mapping_id']} — source-mapped candidate",
                 'Status: Structurally checked; text equivalence has not been individually verified.',
                 f"Evidence: {evidence['name']}, line {selected['source_line']}: {selected['source_rule']}",
                 f"Mapping source: {evidence['url']}"]
    else:
        lines = [f"Mapping: {mapping['mapping_id']} (text-checked pilot)"]
    for source in ('russyn', 'kjv'):
        lines.append(f"\n{manifests[source].get('edition', source)}:")
        names = RUSSIAN_NAMES if source == 'russyn' else NAMES
        for ref, verse in verses[source]:
            lines.append(f"{names[ref['book']]} {ref['chapter']}:{ref['verse']} — {verse['text'] or '[No verse text in this source.]'}")
            for note in verse.get('notes', []):
                parsed = read_note(note['raw_usfm'])
                kind = 'Footnote' if note.get('type') == 'footnote' else 'Cross-reference'
                lines.append(f'  {kind} ({parsed[0]}): {parsed[1]}' if parsed else f"  {kind} (USFM): {note['raw_usfm']}")
        lines.append(f"Source archive SHA-256: {manifests[source]['archive_sha256']}")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', help='Quoted verse reference, e.g. "Псалом 22:1"')
    parser.add_argument('--from', dest='source', required=True, choices=('russyn', 'kjv'), help='Translation of the input reference')
    parser.add_argument('--russyn-data', type=Path, default=Path('output/russyn'))
    parser.add_argument('--kjv-data', type=Path, default=Path('output/kjv'))
    map_group = parser.add_mutually_exclusive_group()
    map_group.add_argument('--source-map', type=Path, help='Optional generated, source-mapped Psalm candidates')
    map_group.add_argument('--psalm-map', type=Path, help='Generated full Psalm map (default: output/psalms_complete_map.json if present)')
    args = parser.parse_args()
    try:
        psalm_map = args.psalm_map or Path('output/psalms_complete_map.json')
        if args.psalm_map is not None and not psalm_map.is_file():
            raise ValueError(f'Psalm map not found: {psalm_map}')
        use_psalm_map = False
        if args.source_map is None and psalm_map.is_file():
            import compare_psalms
            try:
                compare_psalms.parse_ref(args.reference)
                use_psalm_map = True
            except ValueError:
                pass  # Non-Psalm references use the existing pilot.
        if use_psalm_map:
            print(compare_psalms.display(compare_psalms.compare(args.reference, args.source, args.russyn_data, args.kjv_data, psalm_map)))
        else:
            print(format_comparison(compare(args.reference, args.source, args.russyn_data, args.kjv_data, source_map_file=args.source_map)))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
