#!/usr/bin/env python3
"""Build a searchable Matthew Henry SQLite database from the SWORD MHC module."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import struct
import tempfile
import zipfile
import zlib

BOOKS = ('GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV').split()
PREFIX = 'modules/comments/zcom4/mhc/'

class OsisReader(HTMLParser):
    CDATA_CONTENT_ELEMENTS = ()
    RCDATA_CONTENT_ELEMENTS = ()
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.refs = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'reference' and attrs.get('osisref'):
            self.refs.append(attrs['osisref'])
        if tag in ('div', 'title', 'p', 'br', 'lb'):
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('div', 'title', 'p', 'lb'):
            self.parts.append('\n')
    def handle_data(self, data):
        self.parts.append(data)
    def text(self):
        return re.sub(r'\s+', ' ', ''.join(self.parts)).strip()

def records(data):
    if len(data) % 12:
        raise ValueError('SWORD index length is not a multiple of 12')
    return list(struct.iter_unpack('<III', data))

def verses_by_book(directory):
    result = {}
    for book in BOOKS:
        source = json.loads((directory / (book + '.json')).read_text(encoding='utf-8'))
        if source.get('book') != book:
            raise ValueError('Unexpected KJV book: ' + book)
        chapters = {}
        for v in source['verses']:
            chapter, verse = v['chapter'], v['verse']
            if not isinstance(chapter, int) or not isinstance(verse, int):
                raise ValueError('Non-integer KJV reference in ' + book)
            chapters.setdefault(chapter, []).append(verse)
        if sorted(chapters) != list(range(1, source['chapter_count'] + 1)):
            raise ValueError('Non-contiguous chapters in ' + book)
        for ch, vv in chapters.items():
            if vv != list(range(1, len(vv)+1)):
                raise ValueError(f'Non-contiguous verses in {book} {ch}')
        result[book] = chapters
    if sum(len(v) for ch in result.values() for v in ch.values()) != 31102:
        raise ValueError('Expected complete KJV dataset with 31,102 verses')
    return result

def check_config(z):
    config = z.read('mods.d/mhc.conf').decode('utf-8-sig')
    settings = dict(line.strip().split('=', 1) for line in config.splitlines() if '=' in line and not line.lstrip().startswith('#'))
    for key, expected in {'ModDrv':'zCom4', 'CompressType':'ZIP', 'BlockType':'BOOK', 'Versification':'KJV', 'Encoding':'UTF-8', 'SourceType':'OSIS'}.items():
        if settings.get(key, '').strip().lower() != expected.lower():
            raise ValueError(f'Unsupported MHC configuration {key}: {settings.get(key)!r}')
    return settings

def build(archive, kjv, maps, output):
    chapters = verses_by_book(kjv)
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}')
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = tempfile.NamedTemporaryFile(prefix='.mhc-', suffix='.sqlite3', dir=output.parent, delete=False)
    temp.close(); temp_path = Path(temp.name)
    try:
        con = sqlite3.connect(temp_path)
        con.executescript('''
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE comments (id INTEGER PRIMARY KEY, testament TEXT NOT NULL, block INTEGER NOT NULL, byte_offset INTEGER NOT NULL, byte_length INTEGER NOT NULL, osis TEXT NOT NULL, text TEXT NOT NULL, UNIQUE(testament,block,byte_offset,byte_length));
        CREATE VIRTUAL TABLE comment_search USING fts5(text, content='comments', content_rowid='id');
        CREATE TABLE comment_verses (comment_id INTEGER NOT NULL, book TEXT NOT NULL, chapter INTEGER NOT NULL, verse INTEGER NOT NULL, PRIMARY KEY(comment_id,book,chapter,verse));
        CREATE INDEX comment_verse_lookup ON comment_verses(book,chapter,verse);
        CREATE TABLE comment_crossrefs (comment_id INTEGER NOT NULL, osis_ref TEXT NOT NULL, PRIMARY KEY(comment_id,osis_ref));
        CREATE TABLE verse_mapping (ru_book TEXT, ru_chapter INTEGER, ru_verse INTEGER, kjv_book TEXT, kjv_chapter INTEGER, kjv_verse INTEGER, ru_part TEXT NOT NULL, kjv_part TEXT NOT NULL, status TEXT, evidence TEXT, mapping_id TEXT, PRIMARY KEY(ru_book,ru_chapter,ru_verse,kjv_book,kjv_chapter,kjv_verse,ru_part,kjv_part,mapping_id));
        CREATE INDEX mapping_ru_lookup ON verse_mapping(ru_book,ru_chapter,ru_verse);
        ''')
        with zipfile.ZipFile(archive) as z:
            config = check_config(z)
            meta = {'source':'Matthew Henry Commentary, SWORD MHC', 'module_version':config.get('Version',''), 'license_as_declared':config.get('DistributionLicense',''), 'versification':'KJV', 'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(), 'format':'mhc-sqlite-v1'}
            con.executemany('INSERT INTO metadata VALUES (?,?)', meta.items())
            for testament, books in (('ot', BOOKS[:39]), ('nt', BOOKS[39:])):
                index = records(z.read(PREFIX+testament+'.bzv'))
                blocks = records(z.read(PREFIX+testament+'.bzs'))
                compressed = z.read(PREFIX+testament+'.bzz')
                cursor = 2
                seen = {}
                for block_num, book in enumerate(books,1):
                    if cursor >= len(index) or index[cursor][0] != block_num:
                        raise ValueError(f'Book index mismatch at {book}')
                    offset, length, expected_size = blocks[block_num]
                    raw = zlib.decompress(compressed[offset:offset+length])
                    if len(raw) != expected_size:
                        raise ValueError(f'Invalid compressed block size for {book}')
                    cursor += 1 # book introduction
                    for chapter, vv in sorted(chapters[book].items()):
                        cursor += 1 # chapter introduction
                        for verse in vv:
                            if cursor >= len(index): raise ValueError('Truncated verse index')
                            block, start, size = index[cursor]; cursor += 1
                            if size == 0: continue
                            if block != block_num or start + size > len(raw):
                                raise ValueError(f'Invalid verse offset {book} {chapter}:{verse}')
                            key = (block,start,size)
                            if key not in seen:
                                osis = raw[start:start+size].decode('utf-8')
                                parser = OsisReader(); parser.feed(osis); parser.close()
                                row = con.execute('INSERT INTO comments(testament,block,byte_offset,byte_length,osis,text) VALUES (?,?,?,?,?,?)',(testament,block,start,size,osis,parser.text()))
                                cid = row.lastrowid; seen[key] = cid
                                con.execute('INSERT INTO comment_search(rowid,text) VALUES (?,?)',(cid,parser.text()))
                                con.executemany('INSERT OR IGNORE INTO comment_crossrefs VALUES (?,?)', ((cid, ref) for ref in parser.refs))
                            con.execute('INSERT OR IGNORE INTO comment_verses VALUES (?,?,?,?)',(seen[key],book,chapter,verse))
                if cursor != len(index):
                    raise ValueError(f'{testament} verse index length mismatch: {cursor} != {len(index)}')
        for path in maps:
            doc = json.loads(path.read_text(encoding='utf-8'))
            mapid = doc['mapping_id']
            manifest = json.loads((kjv / 'manifest.json').read_text(encoding='utf-8'))
            if doc['sources']['kjv']['archive_sha256'] != manifest['archive_sha256']:
                raise ValueError('KJV dataset and mapping source checksums do not match')
            con.execute('INSERT INTO metadata VALUES (?,?)',('mapping_sha256:'+mapid,hashlib.sha256(path.read_bytes()).hexdigest()))
            for rel in doc['relationships']:
                for ru in rel['russyn']:
                    for en in rel['kjv']:
                        if not all(isinstance(x.get('verse'),int) and x['verse'] > 0 for x in (ru,en)):
                            continue # headings cannot be represented as ordinary verses
                        con.execute('INSERT OR IGNORE INTO verse_mapping VALUES (?,?,?,?,?,?,?,?,?,?,?)', (ru['book'],ru['chapter'],ru['verse'],en['book'],en['chapter'],en['verse'],ru.get('part') or '',en.get('part') or '',rel['status'],json.dumps(rel.get('evidence'),ensure_ascii=False),mapid))
        con.commit()
        stats = {name:con.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in ('comments','comment_verses','comment_crossrefs','verse_mapping')}
        con.close()
        temp_path.rename(output)
        return stats
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--kjv-dir', type=Path, required=True, help='Generated KJV JSON book directory')
    p.add_argument('--mapping', type=Path, action='append', default=[], help='Generated Russian–KJV mapping; repeat for Psalms and other books')
    p.add_argument('--output', type=Path, required=True)
    a=p.parse_args()
    print(json.dumps(build(a.archive,a.kjv_dir,a.mapping,a.output),ensure_ascii=False,indent=2))
if __name__ == '__main__': main()
