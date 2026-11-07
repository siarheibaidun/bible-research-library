#!/usr/bin/env python3
"""Show one chapter or a verse range from a generated WEB dataset."""
import argparse
import json
import re
import sys
from pathlib import Path
from lookup_verse import ALIASES, NAMES, RUSSIAN_NAMES, normalize, read_note


def parse_passage(reference):
    match = re.fullmatch(r'\s*(.+?)\s+(\d+)(?::(\d+)(?:\s*[-–]\s*(\d+))?)?\s*', reference)
    if not match:
        raise ValueError('Use "John 3", "John 3:16" or "John 3:16-18".')
    code = ALIASES.get(normalize(match.group(1)))
    if not code:
        raise ValueError(f'Unknown book: {match.group(1)}.')
    chapter = int(match.group(2))
    start = int(match.group(3)) if match.group(3) else None
    end = int(match.group(4)) if match.group(4) else start
    if chapter < 1 or (start is not None and (start < 1 or end < start)):
        raise ValueError('Use positive numbers and an ascending verse range.')
    return code, chapter, start, end


def passage(directory, reference):
    code, chapter, start, end = parse_passage(reference)
    try:
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8'))
        book = json.loads((directory / f'{code}.json').read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise ValueError(f'Dataset is incomplete: {exc.filename}. Generate it first.') from exc
    if book['book'] != code:
        raise ValueError(f'{code}.json has an unexpected book identifier.')
    records = [v for v in book['verses'] if v['chapter'] == chapter and (start is None or start <= v['verse'] <= end)]
    if not records:
        raise ValueError(f'No verses found for {reference}.')
    numbers = [v['verse'] for v in records]
    if start is not None and (len(numbers) != end - start + 1 or any(n != start + i for i, n in enumerate(numbers))):
        raise ValueError(f'One or more requested verses were not found for {reference}.')
    return code, chapter, records, book, manifest


def format_passage(result):
    code, chapter, records, book, manifest = result
    name = RUSSIAN_NAMES.get(code, NAMES[code]) if manifest.get('language') == 'ru' else NAMES[code]
    lines = [f'{name} {chapter}']
    for verse in records:
        lines.append(f"{verse['verse']}. {verse['text'] or '[No verse text in this source.]'}")
        for note in verse.get('notes', []):
            title = 'Footnote' if note.get('type') == 'footnote' else 'Cross-reference'
            parsed = read_note(note['raw_usfm'])
            if parsed:
                lines.append(f'  {title} ({parsed[0]}): {parsed[1]}')
            else:
                lines.append(f"  {title} (original USFM): {note['raw_usfm']}")
    lines.extend(['', f"Source: {manifest.get('edition', 'Unknown edition')}",
                  f"Source file: {book.get('source_file', 'unknown')}",
                  f"Archive SHA-256: {manifest.get('archive_sha256', 'unknown')}"])
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', help='Quoted chapter or range, e.g. "John 3:16-18"')
    parser.add_argument('--data', type=Path, default=Path('output/web'), help='Generated dataset directory')
    args = parser.parse_args()
    try:
        print(format_passage(passage(args.data, args.reference)))
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
