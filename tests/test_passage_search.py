import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import lookup_passage
import search_verses


class PassageSearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        (self.path / 'manifest.json').write_text(json.dumps({'edition': 'WEB', 'archive_sha256': 'test'}))
        self.verses = [
            {'chapter': 3, 'verse': 1, 'text': 'God is love.', 'notes': []},
            {'chapter': 3, 'verse': 2, 'text': '', 'notes': [{'type': 'footnote', 'raw_usfm': r'\f + \fr 3:2 \ft Note only.\f*'}]},
            {'chapter': 3, 'verse': 3, 'text': 'Love one another.', 'notes': []}]
        (self.path / 'JHN.json').write_text(json.dumps({'book': 'JHN', 'source_file': 'JHN.usfm', 'verses': self.verses}))

    def test_passage_range_chapter_and_notes(self):
        result = lookup_passage.passage(self.path, 'John 3:1-2')
        rendered = lookup_passage.format_passage(result)
        self.assertIn('1. God is love.', rendered)
        self.assertIn('[No verse text in this source.]', rendered)
        self.assertIn('Note only.', rendered)
        self.assertEqual(len(lookup_passage.passage(self.path, 'JHN 3')[2]), 3)
        for reference in ('John 3:0-1', 'John 3:3-2', 'John 3:2-4', 'John 3:1-4:2'):
            with self.assertRaises(ValueError):
                lookup_passage.passage(self.path, reference)

    def test_search_literal_case_insensitive_limit_and_errors(self):
        rows, total, _ = search_verses.search(self.path, 'LOVE', 'John', 1)
        self.assertEqual(total, 2)
        self.assertEqual(rows[0][1]['verse'], 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(search_verses.search(self.path, 'absent', 'John')[1], 0)
        for term, book, limit in [('', 'John', 1), ('love', 'Unknown', 1), ('love', 'John', 0)]:
            with self.assertRaises(ValueError):
                search_verses.search(self.path, term, book, limit)
        with self.assertRaises(ValueError):
            search_verses.search(self.path, 'love')  # Missing other books must not silently yield partial results.


if __name__ == '__main__':
    unittest.main()
