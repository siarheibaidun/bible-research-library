import os,sqlite3,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import semantic_search as s

@unittest.skipUnless(os.getenv('SEMANTIC_TEST_DB'),'Set SEMANTIC_TEST_DB to a built or preview index')
class SemanticSearchTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.db=sqlite3.connect(Path(os.environ['SEMANTIC_TEST_DB']).resolve().as_uri()+'?mode=ro',uri=True)
 @classmethod
 def tearDownClass(cls):cls.db.close()
 def test_dense_russian_parent_question(self):
  r=s.search(self.db,'Как родителям воспитывать детей?',['russyn'],30,[])
  self.assertEqual(r['model'],'intfloat/multilingual-e5-small')
  self.assertTrue(any(x['book'] in ('EPH','COL','PRO') and x['chapter'] in (6,3,22) for x in r['results']))
  self.assertTrue(all(x['translation']=='russyn' for x in r['results']))
 def test_hybrid(self):
  r=s.search(self.db,'воспитание детей',['russyn'],20,[('russyn','детей')])
  self.assertTrue(any('детей' in x['lexical_terms'] for x in r['results']))
 def test_empty(self):
  with self.assertRaises(ValueError):s.search(self.db,'  ',['russyn'],10,[])

@unittest.skipUnless(os.getenv('SEMANTIC_FULL_TEST_DB'),'Set SEMANTIC_FULL_TEST_DB for cross-language tests')
class CrossLanguageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.db=sqlite3.connect(Path(os.environ['SEMANTIC_FULL_TEST_DB']).resolve().as_uri()+'?mode=ro',uri=True)
 @classmethod
 def tearDownClass(cls):cls.db.close()
 def test_three_query_languages(self):
  for query,edition in [('Как родителям воспитывать детей?','russyn'),('How should parents raise their children?','kjv'),('Hoe moeten ouders hun kinderen opvoeden?','nld1917')]:
   with self.subTest(query=query):
    r=s.search(self.db,query,[edition],50,[])
    self.assertTrue(any(x['book'] in ('EPH','COL','PRO') and x['chapter'] in (6,3,22) for x in r['results']))
 def test_cross_lingual_query(self):
  r=s.search(self.db,'Hoe moeten ouders hun kinderen opvoeden?',['russyn'],50,[])
  self.assertTrue(any(x['book'] in ('EPH','COL','PRO') and x['chapter'] in (6,3,22) for x in r['results']))
if __name__=='__main__':unittest.main()
