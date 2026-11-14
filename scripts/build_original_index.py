#!/usr/bin/env python3
"""Import reviewed Hebrew, Greek and Dutch USFM sources with conservative KJV mappings."""
import argparse, collections, hashlib, json, re, sqlite3, unicodedata, zipfile
from pathlib import Path
BOOKS = ('GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV').split()
OSIS = dict(zip('Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John 2John 3John Jude Rev'.split(), BOOKS))
MARK = re.compile(r'(?m)^\\(c|v)\s+(\d+)(?=\s)')
WORD = re.compile(r'\\w\s+([^|\\]+)\|([^\\]+)\\w\*', re.S)
NOTES = re.compile(r'\\(f|x)\s+.*?\\\1\*',re.S)
ATTR = re.compile(r'([\w-]+)="([^"]*)"')
REF = r'([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)(?:!([A-Za-z0-9]+))?'
EXPR = re.compile('^'+REF+'(?:-'+REF+')?$')

def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(c))

def parse_book(data, name):
    text=data.decode('utf-8-sig'); m=re.search(r'(?m)^\\id\s+(\S+)',text)
    if not m or m[1] not in BOOKS: raise ValueError('Invalid book '+name)
    book=m[1]; markers=list(MARK.finditer(text)); chapter=None; rows=[]; seen=set()
    for i,match in enumerate(markers):
        n=int(match[2])
        if match[1]=='c': chapter=n; continue
        if chapter is None or (chapter,n) in seen: raise ValueError(f'Invalid verse {book} {chapter}:{n}')
        seen.add((chapter,n)); raw=text[match.end():markers[i+1].start() if i+1<len(markers) else len(text)].strip()
        notes=[x.group(0) for x in NOTES.finditer(raw)]; body=NOTES.sub('',raw)
        tokens=[]
        def replace(w):
            word=w[1]; tokens.append({'text':word,**dict(ATTR.findall(w[2]))});return word
        body=WORD.sub(replace,body)
        body=re.sub(r'(?m)^\\(?:s\d*|d|sp|ms\d*|cl)\s+[^\n]*','',body)
        body=re.sub(r'\\(?:p|m|mi|nb|b|q\d*|li\d*|pi\d*)\b','',body)
        body=' '.join(body.split())
        if '\\' in body: raise ValueError(f'Unsupported marker {book} {chapter}:{n}: {body[body.index(chr(92)):][:80]}')
        if not body: raise ValueError(f'Empty verse {book} {chapter}:{n}')
        rows.append((book,chapter,n,body,raw,json.dumps(tokens,ensure_ascii=False),json.dumps(notes,ensure_ascii=False)))
    return book,rows

def load(zpath, expected):
    with zipfile.ZipFile(zpath) as z:
        result={}
        for name in z.namelist():
            if not name.lower().endswith('.usfm'):continue
            data=z.read(name); m=re.search(rb'(?m)^\\id\s+(\S+)',data)
            if not m: raise ValueError('missing book ID '+name)
            if m[1].decode() in ('FRT','GLO'):continue
            book,rows=parse_book(data,name)
            if book in result:raise ValueError('Duplicate '+book)
            result[book]=(name,hashlib.sha256(data).hexdigest(),rows)
        if set(result)!=set(expected):raise ValueError(f'Book mismatch missing={set(expected)-set(result)} extra={set(result)-set(expected)}')
        return result

def exp(expr,index):
    m=EXPR.fullmatch(expr.strip())
    if not m: raise ValueError('unsupported expression')
    b,c,v,p,b2,c2,v2,p2=m.groups()
    if b not in OSIS or (b2 and b2!=b):raise ValueError('unknown/cross-book reference')
    book=OSIS[b]; start=(int(c),int(v)); end=(int(c2),int(v2)) if b2 else start
    seq=sorted(set(index.get(book,())) | ({start} if start[1]==0 else set()) | ({end} if end[1]==0 else set()))
    try: out=seq[seq.index(start):seq.index(end)+1]
    except ValueError:raise ValueError('missing range endpoint')
    if not out:raise ValueError('reversed range')
    return [(book,c,v,p if i==0 else (p2 if i==len(out)-1 else None)) for i,(c,v) in enumerate(out)]

def build(he,gr,nl,kjv_db,rules,out):
    sources={'hboWLC':(he,BOOKS[:39]),'ugnt':(gr,BOOKS[39:]),'nld1917':(nl,BOOKS)}
    src={k:load(p,books) for k,(p,books) in sources.items()}
    kjv=sqlite3.connect(f'{kjv_db.resolve().as_uri()}?mode=ro',uri=True)
    meta=dict(kjv.execute('select key,value from metadata'))
    if meta.get('kjv_archive_sha256')!='069646cd8722f6d57750d3b35d378181f9446dc3abeb81a554fd51b57c928689':raise ValueError('Unexpected KJV edition')
    if out.exists():raise FileExistsError(str(out))
    db=sqlite3.connect(out)
    db.executescript('''CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE verse(source TEXT,book TEXT,chapter INTEGER,verse INTEGER,text TEXT,folded TEXT,raw_usfm TEXT,tokens TEXT,notes TEXT,source_file TEXT,PRIMARY KEY(source,book,chapter,verse));
    CREATE INDEX verse_lookup ON verse(source,book,chapter,verse);
    CREATE TABLE mapping(source TEXT,book TEXT,chapter INTEGER,verse INTEGER,kjv_book TEXT,kjv_chapter INTEGER,kjv_verse INTEGER,kjv_part TEXT,status TEXT,evidence TEXT,UNIQUE(source,book,chapter,verse,kjv_book,kjv_chapter,kjv_verse,kjv_part,status));
    CREATE INDEX map_kjv ON mapping(kjv_book,kjv_chapter,kjv_verse);
    CREATE TABLE unresolved(source TEXT,book TEXT,chapter INTEGER,verse INTEGER,reason TEXT);
    CREATE TABLE rule_issues(line INTEGER,rule TEXT,reason TEXT);
    ''')
    for source,(path,_) in sources.items():
        with zipfile.ZipFile(path) as z:
            notices=[name for name in z.namelist() if name.endswith(('copr.htm','LICENSE.md','manifest.yaml'))]
            for name in notices:
                db.execute('INSERT INTO metadata VALUES (?,?)',(source+':notice:'+name,z.read(name).decode('utf-8-sig')))
        db.execute('INSERT INTO metadata VALUES (?,?)',(source+'_sha256',hashlib.sha256(path.read_bytes()).hexdigest()))
        for book,(name,digest,rows) in src[source].items():
            db.execute('INSERT INTO metadata VALUES (?,?)',(source+':file:'+book,digest))
            db.executemany('INSERT INTO verse VALUES (?,?,?,?,?,?,?,?,?,?)',((source,b,c,v,t,fold(t),raw,tokens,notes,name) for b,c,v,t,raw,tokens,notes in rows))
    db.executemany('INSERT INTO metadata VALUES (?,?)', [('format','original-index-v1'),('hboWLC_source','eBible.org, Westminster Leningrad Codex; text public domain; morphology CC BY-SA 3.0'),('ugnt_source','unfoldingWord Greek New Testament v0.34; CC BY-SA 4.0'),('nld1917_source','eBible.org, De Heilige Schrift 1917; public domain'),('kjv_source_sha256',meta['kjv_archive_sha256']),('leningrad_rules_sha256',hashlib.sha256(rules.read_bytes()).hexdigest()),('leningrad_rules_license','CrossWire JSword LGPL-2.1-or-later'),('leningrad_rules_text',rules.read_text(encoding='utf-8-sig')),('hboWLC_url','https://ebible.org/Scriptures/hboWLC_usfm.zip'),('ugnt_url','https://git.door43.org/unfoldingWord/el-x-koine_ugnt/archive/v0.34.zip'),('nld1917_url','https://ebible.org/Scriptures/nld_usfm.zip'),('mapping_warning','Candidates based on stated rules or same-reference; not individually text-verified; partial and headings preserved.')])
    indexes={}
    for source in sources:
        indexes[source]={book: [(row[1],row[2]) for row in item[2]] for book,item in src[source].items()}
    ki=collections.defaultdict(list)
    for b,c,v in kjv.execute("select book,chapter,verse from location where translation='kjv'"):ki[b].append((c,v))
    explicit=collections.defaultdict(list); unsafe=set(); issue=[]
    for no,line in enumerate(rules.read_text(encoding='utf-8-sig').splitlines(),1):
        line=line.strip()
        if not line or line.startswith(('#','!')) or '=' not in line:continue
        l,r=line.split('=',1)
        try:
            left=exp(l,indexes['hboWLC']);right=exp(r,ki)
            if len(left)==len(right): pairs=zip(left,([x] for x in right))
            elif len(left)==1:pairs=[(left[0],right)]
            elif len(right)==1:pairs=((x,right) for x in left)
            else:raise ValueError(f'unsupported cardinality {len(left)}:{len(right)}')
            for a,targets in pairs:explicit[a[:3]].append((targets,no,line))
        except ValueError as ex:
            issue.append((no,line,str(ex)))
            for item in re.finditer(REF,l):
                b,c,v,_=item.groups()
                if b in OSIS:unsafe.add((OSIS[b],int(c)))
    db.executemany('INSERT INTO rule_issues VALUES (?,?,?)',issue)
    counts={};
    for source in sources:
        for book,seq in indexes[source].items():
            for chapter,verse in seq:
                key=(book,chapter,verse); entries=explicit.get(key,[]) if source=='hboWLC' else []
                if source=='hboWLC' and (book,chapter) in unsafe:
                    db.execute('INSERT INTO unresolved VALUES (?,?,?,?,?)',(source,book,chapter,verse,'unsupported rule affects chapter'));continue
                if entries:
                    for targets,no,line in entries:
                        for tb,tc,tv,part in targets:
                            if (tc,tv) not in ki[tb]:
                                db.execute('INSERT INTO unresolved VALUES (?,?,?,?,?)',(source,book,chapter,verse,f'KJV target missing {tb} {tc}:{tv}; rule {no}'));continue
                            db.execute('INSERT OR IGNORE INTO mapping VALUES (?,?,?,?,?,?,?,?,?,?)',(source,book,chapter,verse,tb,tc,tv,part or '', 'published_rule_candidate',f'CrossWire Leningrad line {no}: {line}'))
                elif (chapter,verse) in ki[book]:
                    db.execute('INSERT OR IGNORE INTO mapping VALUES (?,?,?,?,?,?,?,?,?,?)',(source,book,chapter,verse,book,chapter,verse,'','same_reference_candidate','Reference-only candidate; not text verified'))
                else:db.execute('INSERT INTO unresolved VALUES (?,?,?,?,?)',(source,book,chapter,verse,'No KJV numbered target; no correspondence inferred'))
    db.commit()
    print('source counts',db.execute('select source,count(*) from verse group by source').fetchall());print('mapping counts',db.execute('select source,status,count(*) from mapping group by source,status').fetchall());print('unresolved',db.execute('select source,count(*) from unresolved group by source').fetchall());print('rule issues',issue);print('integrity',db.execute('pragma integrity_check').fetchone());db.close();kjv.close()

def main():
    p=argparse.ArgumentParser();p.add_argument('--he',required=True,type=Path);p.add_argument('--greek',required=True,type=Path);p.add_argument('--dutch',required=True,type=Path);p.add_argument('--kjv-index',required=True,type=Path);p.add_argument('--rules',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();build(a.he,a.greek,a.dutch,a.kjv_index,a.rules,a.output)
if __name__=='__main__':main()
