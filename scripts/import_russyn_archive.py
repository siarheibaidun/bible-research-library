#!/usr/bin/env python3
"""Import the verified Russian Synodal USFM archive into per-book JSON."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from import_web_archive import BOOKS, parse_book

EXPECTED_SHA256 = '9af20fe73fff9370acc8fd03cc0ffa718e1cf107d83fc401d41dcadc6c4e4a88'


def import_archive(archive, output):
    data = archive.read_bytes()
    archive_hash = hashlib.sha256(data).hexdigest()
    if archive_hash != EXPECTED_SHA256:
        raise ValueError('Unrecognized archive checksum; verify the edition before importing.')
    books = {}
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            if not info.filename.endswith('.usfm'):
                continue
            result = parse_book(z.read(info), info.filename)
            code = result['book']
            if code in books:
                raise ValueError(f'Duplicate book {code}.')
            books[code] = result
    if set(books) != set(BOOKS):
        raise ValueError(f'Unexpected book set: missing {sorted(set(BOOKS) - set(books))}.')
    output.mkdir(parents=True, exist_ok=True)
    for code in BOOKS:
        (output / f'{code}.json').write_text(json.dumps(books[code], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'archive_filename': archive.name, 'archive_sha256': archive_hash,
                'edition': 'Синодальный перевод (russyn), eBible.org', 'language': 'ru',
                'source_url': None, 'publisher_page': 'https://ebible.org/find/details.php?id=russyn',
                'versification': None, 'book_count': len(BOOKS),
                'chapter_count': sum(b['chapter_count'] for b in books.values()),
                'verse_count': sum(b['verse_count'] for b in books.values()),
                'books': [{'book': code, 'source_file': books[code]['source_file'],
                           'source_sha256': books[code]['source_sha256'], 'chapters': books[code]['chapter_count'],
                           'verses': books[code]['verse_count']} for code in BOOKS]}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        manifest = import_archive(args.archive, args.output)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        parser.exit(1, f'Error: {exc}\n')
    print(f"Imported {manifest['book_count']} books, {manifest['chapter_count']} chapters, {manifest['verse_count']} verses")


if __name__ == '__main__':
    main()
