import importlib.util
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
imp = load('import_mhc')
lookup = load('lookup_mhc')

class MarkupTests(unittest.TestCase):
    def test_nested_title_and_cross_reference(self):
        p = imp.OsisReader()
        p.feed('<title>Creation <hi type="italic">light</hi></title><reference osisRef="Gen.1.3-Gen.1.5">verses 3–5</reference>')
        self.assertEqual(p.text(), 'Creation light verses 3–5')
        self.assertEqual(p.refs, ['Gen.1.3-Gen.1.5'])
    def test_bad_sword_index(self):
        with self.assertRaises(ValueError): imp.records(b'bad')

@unittest.skipUnless(os.environ.get('MHC_TEST_DB'), 'Set MHC_TEST_DB to an imported archive to run integration tests')
class ArchiveIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db=Path(os.environ['MHC_TEST_DB'])
    def get(self, lang, book, chapter, verse):
        return lookup.lookup(self.db,lang,book,chapter,verse)
    def test_shared_genesis_fragment(self):
        comments=[self.get('kjv','GEN',1,n)['comments'] for n in (3,4,5)]
        self.assertEqual([c[0]['id'] for c in comments], [comments[0][0]['id']]*3)
        self.assertIn('And God said, Let there be light', comments[0][0]['text'])
    def test_john_cross_reference(self):
        result=self.get('kjv','JHN',3,16)
        self.assertTrue(any('Num.21.6-Num.21.9' in c['cross_references'] for c in result['comments']))
    def test_psalm_mapping(self):
        result=self.get('russyn','PSA',22,1)
        self.assertTrue(any((x['kjv_chapter'],x['kjv_verse'])==(23,1) for x in result['kjv_mappings']))
        self.assertTrue(any('The Lord is my shepherd' in x['text'] for x in result['comments']))
    def test_missing_mapping_does_not_guess(self):
        result=self.get('russyn','PSA',999,1)
        self.assertEqual(result['comments'],[])
        self.assertEqual(result['note'],'No mapping available')
    def test_missing_comment_does_not_guess(self):
        self.assertEqual(self.get('kjv','JOS',18,1)['comments'],[])
    def test_full_text_search(self):
        with sqlite3.connect(self.db) as db:
            self.assertGreater(db.execute("SELECT count(*) FROM comment_search WHERE comment_search MATCH ?", ('Nicodemus',)).fetchone()[0],0)

if __name__ == '__main__': unittest.main()
