import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import import_russyn_archive
import lookup_verse
import lookup_passage
import search_verses


class RussianTests(unittest.TestCase):
    def test_book_names_and_ambiguous_kings(self):
        self.assertEqual(lookup_verse.parse_reference('Иоанна 3:16'), ('JHN', 3, 16))
        self.assertEqual(lookup_verse.parse_reference('1 Иоанна 4:8'), ('1JN', 4, 8))
        self.assertEqual(lookup_verse.parse_reference('3 Царств 1:1'), ('1KI', 1, 1))
        self.assertEqual(lookup_verse.parse_reference('4 Царств 1:1'), ('2KI', 1, 1))
        self.assertEqual(lookup_verse.parse_reference('John 3:16'), ('JHN', 3, 16))

    def test_russian_lookup_passage_and_search(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'manifest.json').write_text(json.dumps({'edition': 'Синодальный', 'language': 'ru'}), encoding='utf8')
            book = {'book': 'JHN', 'source_file': 'john.usfm', 'verses': [
                {'chapter': 3, 'verse': 16, 'text': 'Бог есть любовь', 'notes': []},
                {'chapter': 3, 'verse': 17, 'text': 'Мир', 'notes': []}]}
            (folder / 'JHN.json').write_text(json.dumps(book, ensure_ascii=False), encoding='utf8')
            self.assertIn('Иоанна 3:16', lookup_verse.format_result(lookup_verse.lookup(folder, 'Ин 3:16')))
            self.assertEqual(len(lookup_passage.passage(folder, 'Иоанна 3:16-17')[2]), 2)
            self.assertEqual(search_verses.search(folder, 'БОГ', book='Иоанна')[1], 1)

    def test_unverified_archive_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'unknown.zip'
            src.write_bytes(b'unknown')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                import_russyn_archive.import_archive(src, Path(tmp) / 'out')
            self.assertFalse((Path(tmp) / 'out').exists())


if __name__ == '__main__':
    unittest.main()
