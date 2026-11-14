import importlib.util,os,sqlite3,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(n):
 s=importlib.util.spec_from_file_location(n,ROOT/'scripts'/f'{n}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
imp=load('build_original_index');search=load('original_search')
class UnitTests(unittest.TestCase):
 def test_unicode(self):
  self.assertEqual(search.fold('λόγος'),search.fold('λογος'));self.assertEqual(search.fold('בְּרֵאשִׁית'),search.fold('בראשית'))
 def test_word_notes_and_raw(self):
  sample='\\id GEN\n\\c 1\n\\v 1 \\w בְּרֵאשִׁית|strong="H7225" x-morph="HR/N"\\w* \\f + \\ft note\\f*'.encode()
  b,rows=imp.parse_book(sample,'GEN.usfm');self.assertEqual(b,'GEN');self.assertEqual(rows[0][3],'בְּרֵאשִׁית');self.assertIn('H7225',rows[0][5]);self.assertIn('note',rows[0][6]);self.assertIn('\\w ',rows[0][4])
 def test_range(self):
  idx={'PSA':[(3,n) for n in range(1,10)]}
  self.assertEqual(len(imp.exp('Ps.3.1-Ps.3.9',idx)),9)
  with self.assertRaises(ValueError):imp.exp('Ps.3.1-Ps.4.4',idx)
@unittest.skipUnless(os.getenv('ORIGINAL_TEST_DB') and os.getenv('BIBLE_TEST_DB'),'Set integration database paths')
class IntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.db=search.connect(Path(os.environ['ORIGINAL_TEST_DB']));cls.bible=sqlite3.connect(Path(os.environ['BIBLE_TEST_DB']).resolve().as_uri()+'?mode=ro',uri=True)
 @classmethod
 def tearDownClass(cls):cls.db.close();cls.bible.close()
 def test_sources(self):
  self.assertEqual(dict(self.db.execute('select source,count(distinct book) from verse group by source')) ,{'hboWLC':39,'ugnt':27,'nld1917':66})
  self.assertEqual(self.db.execute('pragma integrity_check').fetchone()[0],'ok')
 def test_word_analysis(self):
  v=search.verse(self.db,'ugnt','JHN',1,1,True);self.assertTrue(any(t.get('lemma')=='λόγος' and t.get('x-morph') for t in v['verse']['tokens']))
 def test_diacritics_search(self):self.assertGreater(search.search(self.db,'ugnt','λογος',5,0)['total'],0)
 def test_psalms_shift(self):
  r=search.cross(self.db,self.bible,'kjv','PSA',3,1,['hboWLC']);self.assertTrue(any(x['target']['verse']==2 and x['target_mapping']['status']=='published_rule_candidate' for x in r['results']))
  r=search.cross(self.db,self.bible,'russyn','PSA',22,1,['hboWLC','nld1917']);self.assertEqual({x['target']['source'] for x in r['results']},{'hboWLC','nld1917'});self.assertTrue(all(x['kjv_bridge']['chapter']==23 for x in r['results']))
 def test_unresolved_no_guess(self):
  r=search.verse(self.db,'ugnt','3JN',1,15);self.assertEqual(r['kjv_mappings'],[]);self.assertTrue(r['unresolved'])
 def test_empty_result(self):self.assertEqual(search.cross(self.db,self.bible,'russyn','PSA',999,1,['hboWLC'])['results'],[])
if __name__=='__main__':unittest.main()
