import importlib.util,sqlite3,sys,tempfile,unittest
from pathlib import Path

SCRIPTS=Path(__file__).parents[1]/'skills'/'bible-research-search'/'scripts'
sys.path.insert(0,str(SCRIPTS))
import question_search

class QuestionSearchTests(unittest.TestCase):
    def test_query_is_literal_and_ranks_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'index.sqlite3';db=sqlite3.connect(p)
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT); CREATE TABLE passage(id INTEGER PRIMARY KEY,book TEXT,chapter INT,start INT,end INT,text TEXT); CREATE VIRTUAL TABLE passage_fts USING fts5(text,content="passage",content_rowid="id");')
            db.execute('INSERT INTO metadata VALUES(?,?)',('source_sha256',question_search.EXPECTED))
            db.execute('INSERT INTO passage VALUES(1,"EPH",6,1,4,?)',('отцы воспитывайте детей наставлении Господнем',))
            db.execute('INSERT INTO passage VALUES(2,"GEN",1,1,1,?)',('родил детей и сынов',))
            db.execute("INSERT INTO passage_fts(passage_fts) VALUES('rebuild')");db.commit();db.close()
            r=question_search.search(p,['детей','отц','воспиты','настав'],10)
            self.assertEqual(r['results'][0]['reference'],'Ефесянам 6:1–4')
            self.assertIn('not vector embeddings',r['method'])
            with self.assertRaises(ValueError):question_search.search(p,['дет* OR отец'],10)
            with self.assertRaises(ValueError):question_search.search(p,[],10)

if __name__=='__main__':unittest.main()
