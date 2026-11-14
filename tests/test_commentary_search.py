import importlib.util
from pathlib import Path
import sqlite3
import unittest

path = Path(__file__).resolve().parents[1] / 'skills/bible-research-search/scripts/commentary_search.py'
spec = importlib.util.spec_from_file_location('commentary_search', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CommentaryTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          CREATE TABLE comments(id INTEGER PRIMARY KEY, text TEXT);
          CREATE TABLE comment_verses(comment_id INTEGER, book TEXT, chapter INTEGER, verse INTEGER);
          CREATE TABLE comment_crossrefs(comment_id INTEGER, osis_ref TEXT);
          CREATE TABLE verse_mapping(ru_book TEXT, ru_chapter INTEGER, ru_verse INTEGER, kjv_book TEXT, kjv_chapter INTEGER, kjv_verse INTEGER, ru_part TEXT, kjv_part TEXT, status TEXT, evidence TEXT, mapping_id TEXT);
          CREATE VIRTUAL TABLE comment_search USING fts5(text);
          INSERT INTO comments VALUES(1, 'The Lord is my shepherd and guide.');
          INSERT INTO comment_search(rowid,text) VALUES(1, 'The Lord is my shepherd and guide.');
          INSERT INTO comment_verses VALUES(1,'PSA',23,1);
          INSERT INTO comment_verses VALUES(1,'PSA',23,2);
          INSERT INTO comment_crossrefs VALUES(1,'John.10.11');
          INSERT INTO verse_mapping VALUES('PSA',22,1,'PSA',23,1,'','','text_checked_pilot','test','test-map');
        ''')
    def tearDown(self): self.db.close()
    def test_russian_verse_and_truncation(self):
        r = mod.verse(self.db,'russyn','PSA',22,1,12)
        self.assertEqual(r['kjv_mappings'][0]['kjv_chapter'],23)
        self.assertEqual(len(r['comments'][0]['kjv_verses']),2)
        self.assertTrue(r['comments'][0]['truncated'])
        self.assertEqual(r['comments'][0]['cross_references'],['John.10.11'])
    def test_missing_reference_no_guess(self):
        r=mod.verse(self.db,'russyn','PSA',99,1,100)
        self.assertEqual(r['comments'],[])
        self.assertEqual(r['note'],'No numbered verse mapping established')
    def test_fts_literal(self):
        r=mod.search(self.db,'shepherd',10,0)
        self.assertEqual(r['total'],1)
        self.assertIn('shepherd',r['results'][0]['excerpt'])
        self.assertEqual(mod.search(self.db,'nonsense',10,0)['total'],0)
    def test_reject_empty_search(self):
        with self.assertRaises(ValueError): mod.search(self.db,'"',10,0)

if __name__ == '__main__': unittest.main()
