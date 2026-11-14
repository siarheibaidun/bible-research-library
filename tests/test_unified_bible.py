import importlib.util,os,sqlite3,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import unified_search as u
@unittest.skipUnless(os.getenv('UNIFIED_TEST_DB'),'Set UNIFIED_TEST_DB')
class UnifiedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.db=u.connect(Path(os.environ['UNIFIED_TEST_DB']))
 @classmethod
 def tearDownClass(cls):cls.db.close()
 def test_directions_ot(self):
  for src in ('russyn','kjv','nld1917','hboWLC'):
   for dest in ('russyn','kjv','nld1917','hboWLC'):
    with self.subTest(src=src,dest=dest):
     r=u.compare(self.db,src,'GEN',1,1,[dest]);self.assertTrue(any(x['verse']['translation']==dest for x in r['results']))
 def test_directions_nt(self):
  for src in ('russyn','kjv','nld1917','ugnt'):
   for dest in ('russyn','kjv','nld1917','ugnt'):
    with self.subTest(src=src,dest=dest):
     r=u.compare(self.db,src,'JHN',1,1,[dest]);self.assertTrue(any(x['verse']['translation']==dest for x in r['results']))
 def test_psalm_shift_forward_reverse(self):
  f=u.compare(self.db,'russyn','PSA',22,1,['hboWLC','nld1917']);self.assertEqual({(x['verse']['translation'],x['verse']['chapter']) for x in f['results']},{('hboWLC',23),('nld1917',23)})
  r=u.compare(self.db,'nld1917','PSA',23,1,['russyn']);self.assertTrue(any(x['verse']['chapter']==22 for x in r['results']))
  h=u.compare(self.db,'hboWLC','PSA',3,2,['kjv']);self.assertTrue(any(x['verse']['chapter']==3 and x['verse']['verse']==1 for x in h['results']))
 def test_morphology_and_note_preservation(self):
  r=u.compare(self.db,'ugnt','JHN',1,1,['ugnt'],True);self.assertTrue(any(t.get('lemma')=='λόγος' and t.get('x-morph') for t in r['selected']['tokens']))
 def test_split_mapping(self):
  r=u.compare(self.db,'ugnt','3JN',1,15,['kjv']);self.assertEqual(r['results'][0]['verse']['verse'],14);self.assertEqual(r['kjv_anchors'][0]['part'],'closing')
  r=u.compare(self.db,'russyn','3JN',1,15,['ugnt']);self.assertEqual([x['verse']['verse'] for x in r['results']],[15])
  r=u.compare(self.db,'ugnt','3JN',1,15,['russyn']);self.assertEqual([x['verse']['verse'] for x in r['results']],[15])
  r=u.compare(self.db,'ugnt','REV',12,18,['kjv']);self.assertEqual(r['results'][0]['verse']['chapter'],13);self.assertEqual(r['kjv_anchors'][0]['part'],'opening');self.assertIn('textual variant',r['kjv_anchors'][0]['evidence'])
  r=u.compare(self.db,'kjv','REV',13,1,['ugnt']);self.assertEqual({(x['verse']['chapter'],x['verse']['verse']) for x in r['results']},{(12,18),(13,1)})
 def test_no_fabricated_target(self):
  r=u.compare(self.db,'russyn','GEN',1,1,['ugnt']);self.assertEqual(r['results'],[]);self.assertEqual(r['missing_targets'],['ugnt'])
 def test_actual_mapping_evidence(self):
  r=u.compare(self.db,'hboWLC','PSA',3,2,['kjv']);self.assertEqual(r['kjv_anchors'][0]['status'],'published_rule_candidate');self.assertIn('CrossWire',r['kjv_anchors'][0]['evidence'])
 def test_lexical_in_three_languages(self):
  for lang,q in [('russyn','любовь'),('kjv','love'),('nld1917','liefde')]:self.assertGreater(u.literal(self.db,lang,q,5,0)['total'],0)
  r=u.topics(self.db,[('russyn','любов'),('kjv','love'),('nld1917','liefde')],30);self.assertEqual({x['translation'] for x in r['results']},{'russyn','kjv','nld1917'})
 def test_names(self):
  for b in ('Johannes','John','Иоанна','JHN'):self.assertEqual(u.bookcode(b),'JHN')
  for b in ('Psalmen','Psalms','Псалом'):self.assertEqual(u.bookcode(b),'PSA')
 def test_integrity(self):self.assertEqual(self.db.execute('pragma integrity_check').fetchone()[0],'ok')
if __name__=='__main__':unittest.main()
