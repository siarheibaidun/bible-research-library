import importlib.util,sqlite3,tempfile,unittest,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
try:
 import build_vector_index as build
except ImportError:
 build=None

class IndexTests(unittest.TestCase):
 @unittest.skipUnless(build and os.getenv('VECTOR_TEST_MODEL') and os.getenv('VECTOR_TEST_TOKENIZER'),'Install vector dependencies and set model and tokenizer paths')
 def test_long_passage_resume(self):
  with tempfile.TemporaryDirectory() as d:
   db=Path(d)/'source.db';out=Path(d)/'vector.db';c=sqlite3.connect(db)
   c.executescript("create table metadata(key text,value text);insert into metadata values('unified_format','bible-unified-v1');create table multilang_passage(id integer,translation text,book text,chapter integer,start integer,end integer,text text);create table verse(source text,book text,chapter integer,verse integer,text text);")
   c.execute('insert into multilang_passage values (1,?,?,?,?,?,?)',('kjv','GEN',1,1,1,'The light shines and God speaks. '*120));c.execute('insert into verse values (?,?,?,?,?)',('hboWLC','GEN',1,1,'בְּרֵאשִׁית בָּרָא'));c.execute('insert into verse values (?,?,?,?,?)',('ugnt','JHN',1,1,'ἐν ἀρχῇ ἦν ὁ λόγος'));c.commit();c.close()
   model=Path(os.environ['VECTOR_TEST_MODEL']);tok=Path(os.environ['VECTOR_TEST_TOKENIZER']);build.build(db,model,tok,out,8,2)
   c=sqlite3.connect(out);before=c.execute('select count(*) from semantic_vectors where passage_id=1').fetchone()[0];self.assertGreater(before,1);c.execute('delete from semantic_vectors where passage_id=1 and part=1');c.execute("update semantic_metadata set value='building' where key='state'");c.commit();c.close()
   build.build(db,model,tok,out,8,2);c=sqlite3.connect(out);self.assertEqual(c.execute('select count(*) from semantic_vectors where passage_id=1').fetchone()[0],before);self.assertEqual(dict(c.execute('select key,value from semantic_metadata'))['state'],'complete');c.close()
if __name__=='__main__':unittest.main()
