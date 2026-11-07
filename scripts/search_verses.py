#!/usr/bin/env python3
"""Search verse text for a case-insensitive literal word or phrase."""
import argparse
import json
import sys
from pathlib import Path
from lookup_verse import ALIASES, NAMES, RUSSIAN_NAMES, normalize


def search(directory, query, book=None, limit=20):
    if not query.strip():
        raise ValueError('Search text must not be empty.')
    if limit < 1:
        raise ValueError('Limit must be at least 1.')
    manifest_path = directory / 'manifest.json'
    if not manifest_path.is_file():
        raise ValueError(f'No manifest.json found in {directory}. Generate the dataset first.')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if book:
        code = ALIASES.get(normalize(book))
        if not code:
            raise ValueError(f'Unknown book: {book}.')
        codes = [code]
    else:
        codes = list(NAMES)
    matches, total = [], 0
    for code in codes:
        path = directory / f'{code}.json'
        if not path.is_file():
            raise ValueError(f'Dataset is missing {code}.json. Regenerate the dataset.')
        data = json.loads(path.read_text(encoding='utf-8'))
        if data['book'] != code:
            raise ValueError(f'{code}.json has an unexpected book identifier.')
        for verse in data['verses']:
            if query.casefold() in verse['text'].casefold():
                total += 1
                if len(matches) < limit:
                    matches.append((code, verse))
    return matches, total, manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('query', help='Literal word or phrase (case-insensitive)')
    parser.add_argument('--book', help='Restrict to a full book name or USFM code')
    parser.add_argument('--limit', type=int, default=20, help='Maximum results to display (default: 20)')
    parser.add_argument('--data', type=Path, default=Path('output/web'), help='Generated dataset directory')
    args = parser.parse_args()
    try:
        matches, total, manifest = search(args.data, args.query, args.book, args.limit)
        print(f'Showing {len(matches)} of {total} matching verses for {args.query!r}:')
        for code, verse in matches:
            name = RUSSIAN_NAMES.get(code, NAMES[code]) if manifest.get('language') == 'ru' else NAMES[code]
            print(f"{name} {verse['chapter']}:{verse['verse']} — {verse['text']}")
        print(f"\nSource: {manifest.get('edition', 'Unknown edition')}")
        print(f"Archive SHA-256: {manifest.get('archive_sha256', 'unknown')}")
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
