#!/usr/bin/env python3
"""Import the 66 books in a WEB USFM archive into per-book JSON files."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

BOOKS = ('GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV').split()
MARKERS = re.compile(r'(?m)^\\(c|v)\s+(\d+)\s*')
TOKEN = re.compile(r'\\(?:f|x)\s+.*?\\(?:f|x)\*|\\\+?w\s+([^|\\]+)\|([^\\]+)\\\+?w\*|\\\+?(?:wj|k|qs|bk|add|nd|tl)\*?|\\(?:p|m|mi|nb|b|q1|q2|li1|pi1)\b', re.DOTALL)
HEADINGS = re.compile(r'(?m)^\\(?:d|sp|ms1|cl|s1)\s+[^\n]*')
STRONG = re.compile(r'\bstrong="([^"]+)"')


def render(raw, where):
    # Headings are retained in raw USFM, but are not part of verse text.
    body = HEADINGS.sub('', raw)
    parts, notes, annotations = [], [], []
    last = 0
    for m in TOKEN.finditer(body):
        parts.append(body[last:m.start()])
        value = m.group(0)
        if value.startswith(('\\f ', '\\x ')):
            kind = 'footnote' if value.startswith('\\f ') else 'cross_reference'
            notes.append({'type': kind, 'raw_usfm': value})
        elif m.group(1) is not None:
            strong = STRONG.search(m.group(2))
            if not strong:
                raise ValueError(f'{where}: unsupported word attributes')
            parts.append(m.group(1))
            annotations.append({'text': m.group(1), 'strong': strong.group(1)})
        last = m.end()
    parts.append(body[last:])
    result = ''.join(parts)
    if '\\' in result:
        raise ValueError(f'{where}: unsupported marker near {result[result.index(chr(92)):][:50]!r}')
    return ' '.join(result.split()), notes, annotations


def parse_book(data, filename):
    text = data.decode('utf-8-sig')
    ident = re.search(r'(?m)^\\id\s+(\S+)', text)
    if not ident or ident.group(1) not in BOOKS:
        raise ValueError(f'{filename}: unsupported book ID')
    book = ident.group(1)
    markers = list(MARKERS.finditer(text))
    chapter = None
    preamble = text[:markers[0].start()] if markers else text
    chapter_preambles = []
    records = []
    seen_chapters = set()
    last_verse = 0
    for i, m in enumerate(markers):
        number = int(m.group(2))
        if m.group(1) == 'c':
            if number in seen_chapters or number != len(seen_chapters) + 1:
                raise ValueError(f'{book}: unexpected chapter {number}')
            seen_chapters.add(number)
            chapter, last_verse = number, 0
            chapter_preambles.append({'chapter': number, 'raw_usfm': text[m.end():markers[i+1].start() if i+1 < len(markers) else len(text)].strip()})
            continue
        if chapter is None or number != last_verse + 1:
            raise ValueError(f'{book} {chapter}: unexpected verse {number}')
        last_verse = number
        raw = text[m.end():markers[i+1].start() if i+1 < len(markers) else len(text)].strip()
        plain, notes, annotations = render(raw, f'{book} {chapter}:{number}')
        if not plain and not notes:
            raise ValueError(f'{book} {chapter}:{number}: empty verse')
        records.append({'book': book, 'chapter': chapter, 'verse': number, 'text': plain,
                        'notes': notes, 'strong_annotations': annotations, 'raw_usfm': raw})
    if not records:
        raise ValueError(f'{filename}: no verses')
    return {'book': book, 'source_file': filename, 'source_sha256': hashlib.sha256(data).hexdigest(),
            'chapter_count': len(seen_chapters), 'verse_count': len(records), 'book_preamble_usfm': preamble,
            'chapter_preambles': chapter_preambles, 'verses': records}


def import_archive(archive, output):
    archive_bytes = archive.read_bytes()
    with zipfile.ZipFile(archive) as z:
        by_book = {}
        for info in z.infolist():
            if not info.filename.endswith('.usfm'):
                continue
            data = z.read(info)
            identity = re.search(rb'(?m)^\\id\s+(\S+)', data)
            if not identity:
                raise ValueError(f'{info.filename}: missing book ID')
            book = identity.group(1).decode('ascii')
            if book in ('FRT', 'GLO'):
                continue
            if book not in BOOKS or book in by_book:
                raise ValueError(f'Unsupported or duplicate book: {book}')
            by_book[book] = parse_book(data, info.filename)
    if set(by_book) != set(BOOKS):
        raise ValueError(f'Book set mismatch; missing: {sorted(set(BOOKS) - set(by_book))}')
    # Only write after the whole source validates successfully.
    output.mkdir(parents=True, exist_ok=True)
    for book in BOOKS:
        (output / f'{book}.json').write_text(json.dumps(by_book[book], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    manifest = {'archive_filename': archive.name, 'archive_sha256': hashlib.sha256(archive_bytes).hexdigest(),
                'edition': 'World English Bible (engwebp), archive copyright notice: 2020 stable text edition',
                'archive_download_url': None, 'versification': None, 'book_count': len(BOOKS),
                'chapter_count': sum(x['chapter_count'] for x in by_book.values()),
                'verse_count': sum(x['verse_count'] for x in by_book.values()),
                'books': [{'book': b, 'source_file': by_book[b]['source_file'], 'source_sha256': by_book[b]['source_sha256'],
                           'chapters': by_book[b]['chapter_count'], 'verses': by_book[b]['verse_count']} for b in BOOKS]}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    m = import_archive(args.archive, args.output)
    print(f"Imported {m['book_count']} books, {m['chapter_count']} chapters, {m['verse_count']} verses")


if __name__ == '__main__':
    main()
