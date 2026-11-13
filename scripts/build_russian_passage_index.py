#!/usr/bin/env python3
"""Create an overlapping Russian Bible passage index using SQLite FTS5."""
import argparse,sqlite3,sys
from pathlib import Path
EXPECTED='9af20fe73fff9370acc8fd03cc0ffa718e1cf107d83fc401d41dcadc6c4e4a88'

def build(source_path,output):
    if not source_path.is_file():raise ValueError('Source Bible index not found.')
    if output.exists():raise ValueError('Output already exists; choose a new file.')
    source=sqlite3.connect(f'{source_path.resolve().as_uri()}?mode=ro',uri=True)
    try:
        metadata=dict(source.execute('SELECT key,value FROM metadata'))
        if metadata.get('russyn_archive_sha256') != EXPECTED:raise ValueError('Unexpected Russian source edition.')
        output.parent.mkdir(parents=True,exist_ok=True)
        out=sqlite3.connect(output)
        try:
            out.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE passage(id INTEGER PRIMARY KEY,book TEXT,chapter INTEGER,start INTEGER,end INTEGER,text TEXT); CREATE VIRTUAL TABLE passage_fts USING fts5(text,content="passage",content_rowid="id",tokenize="unicode61");')
            out.executemany('INSERT INTO metadata VALUES(?,?)',[('source_sha256',EXPECTED),('method','overlapping four-verse windows, two-verse stride; Synodal; lexical FTS5')])
            for (book,) in source.execute("SELECT DISTINCT book FROM location WHERE translation='russyn' AND verse>0 ORDER BY book"):
                for (ch,) in source.execute("SELECT DISTINCT chapter FROM location WHERE translation='russyn' AND book=? AND verse>0 ORDER BY chapter",(book,)):
                    verses=source.execute("SELECT verse,text FROM location WHERE translation='russyn' AND book=? AND chapter=? AND verse>0 ORDER BY verse",(book,ch)).fetchall()
                    for i in range(0,len(verses),2):
                        part=verses[i:i+4];out.execute('INSERT INTO passage(book,chapter,start,end,text) VALUES(?,?,?,?,?)',(book,ch,part[0][0],part[-1][0],' '.join(x[1] for x in part)))
            out.execute("INSERT INTO passage_fts(passage_fts) VALUES('rebuild')");out.commit();count=out.execute('SELECT count(*) FROM passage').fetchone()[0]
        finally:out.close()
        return count
    except Exception:
        if output.exists():output.unlink()
        raise
    finally:source.close()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
    try:print(f'Created {build(a.source,a.output)} passage windows in {a.output}')
    except (OSError,ValueError,sqlite3.Error) as exc:print(f'Error: {exc}',file=sys.stderr);return 1
    return 0
if __name__=='__main__':raise SystemExit(main())
