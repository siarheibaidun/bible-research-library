#!/usr/bin/env python3
"""Import John 3 from the supplied WEB USFM file; no external dependencies."""
import argparse
import hashlib
import json
import re
from pathlib import Path

CHAPTER = re.compile(r'^\\c\s+(\d+)\s*$', re.MULTILINE)
VERSE = re.compile(r'^\\v\s+(\d+)\s+', re.MULTILINE)
# The source's nested word markers use either \\w or \\+w.
TOKEN = re.compile(r'\\f\s+.*?\\f\*|\\\+?w\s+([^|\\]+)\|([^\\]+)\\\+?w\*|\\wj\*?|\\p\b', re.DOTALL)
STRONG = re.compile(r'\bstrong="([^"]+)"')


def parse(source: bytes, filename: str) -> dict:
    data = source.decode('utf-8-sig')
    if not re.search(r'^\\id\s+JHN(?:\s|$)', data, re.MULTILINE):
        raise ValueError('Expected a USFM Gospel of John (\\id JHN).')
    chapters = list(CHAPTER.finditer(data))
    matches = [i for i, m in enumerate(chapters) if m.group(1) == '3']
    if len(matches) != 1:
        raise ValueError('Expected exactly one chapter 3.')
    i = matches[0]
    chapter = data[chapters[i].end():chapters[i+1].start() if i+1 < len(chapters) else len(data)]
    markers = list(VERSE.finditer(chapter))
    if [int(m.group(1)) for m in markers] != list(range(1, 37)):
        raise ValueError('Expected exactly verses 1 through 36 in John 3.')
    records = []
    for n, match in enumerate(markers):
        raw = chapter[match.end():markers[n+1].start() if n+1 < len(markers) else len(chapter)].strip()
        parts, notes, words = [], [], []
        last = 0
        for token in TOKEN.finditer(raw):
            parts.append(raw[last:token.start()])
            value = token.group(0)
            if value.startswith('\\f '):
                ref = re.search(r'\\fr\s+(.+?)(?=\\ft\s)', value, re.DOTALL)
                text = re.search(r'\\ft\s+(.+?)\\f\*', value, re.DOTALL)
                if not ref or not text:
                    raise ValueError(f'Unsupported footnote in verse {match.group(1)}')
                notes.append({'reference': ref.group(1).strip(), 'text': ' '.join(text.group(1).split())})
            elif token.group(1) is not None:
                surface, attrs = token.group(1), token.group(2)
                strong = STRONG.search(attrs)
                if not strong:
                    raise ValueError(f'Unsupported word attributes in verse {match.group(1)}')
                parts.append(surface)
                words.append({'text': surface, 'strong': strong.group(1)})
            last = token.end()
        parts.append(raw[last:])
        rendered = ''.join(parts)
        if '\\' in rendered:
            raise ValueError(f'Unsupported USFM marker in verse {match.group(1)}')
        records.append({'book': 'JHN', 'chapter': 3, 'verse': int(match.group(1)),
                        'text': ' '.join(rendered.split()), 'footnotes': notes,
                        'strong_annotations': words, 'raw_usfm': raw})
    return {'source': {'filename': filename, 'sha256': hashlib.sha256(source).hexdigest(),
                       'book': 'JHN', 'translation': 'World English Bible (as identified in file)',
                       'versification': None, 'archive_provenance': 'not provided'},
            'scope': 'John 3', 'verses': records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Gospel of John USFM file')
    parser.add_argument('output', type=Path, help='Output JSON file')
    args = parser.parse_args()
    result = parse(args.source.read_bytes(), args.source.name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"Imported {len(result['verses'])} verses to {args.output}")


if __name__ == '__main__':
    main()
