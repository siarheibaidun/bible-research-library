import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import compare_translations as compare


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.ru, self.en = root / 'ru', root / 'en'
        self.ru.mkdir(); self.en.mkdir()
        for path, digest, text in [(self.ru, 'ru-hash', 'Русский текст'), (self.en, 'en-hash', 'English text')]:
            (path / 'manifest.json').write_text(json.dumps({'edition': 'test', 'archive_sha256': digest}), encoding='utf-8')
            (path / 'PSA.json').write_text(json.dumps({'book': 'PSA', 'verses': [
                {'chapter': 22 if path == self.ru else 23, 'verse': 1, 'text': text, 'notes': []}]}), encoding='utf-8')
        self.mapping = {'mapping_id': 'test', 'sources': {'russyn': {'archive_sha256': 'ru-hash'}, 'web': {'archive_sha256': 'en-hash'}},
                        'relationships': [{'russyn': [{'book': 'PSA', 'chapter': 22, 'verse': 1}],
                                           'web': [{'book': 'PSA', 'chapter': 23, 'verse': 1}]}]}
        self.map_file = root / 'mapping.json'
        self.save_mapping()

    def save_mapping(self):
        self.map_file.write_text(json.dumps(self.mapping), encoding='utf-8')

    def test_both_directions(self):
        a = compare.format_comparison(compare.compare('Псалом 22:1', 'russyn', self.ru, self.en, self.map_file))
        b = compare.format_comparison(compare.compare('Psalm 23:1', 'web', self.ru, self.en, self.map_file))
        self.assertEqual(a, b)
        self.assertIn('Псалтирь 22:1 — Русский текст', a)
        self.assertIn('Psalms 23:1 — English text', a)

    def test_unmapped_and_ambiguous_are_refused(self):
        with self.assertRaisesRegex(ValueError, 'No reviewed pilot mapping'):
            compare.compare('Psalm 22:1', 'web', self.ru, self.en, self.map_file)
        self.mapping['relationships'].append(self.mapping['relationships'][0]); self.save_mapping()
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            compare.compare('Psalm 23:1', 'web', self.ru, self.en, self.map_file)

    def test_wrong_checksum_and_missing_verse_fail(self):
        self.mapping['sources']['web']['archive_sha256'] = 'wrong'; self.save_mapping()
        with self.assertRaisesRegex(ValueError, 'checksum'):
            compare.compare('Psalm 23:1', 'web', self.ru, self.en, self.map_file)
        self.mapping['sources']['web']['archive_sha256'] = 'en-hash'
        self.mapping['relationships'][0]['web'][0]['verse'] = 2; self.save_mapping()
        with self.assertRaisesRegex(ValueError, 'missing or duplicated'):
            compare.compare('Псалом 22:1', 'russyn', self.ru, self.en, self.map_file)


if __name__ == '__main__':
    unittest.main()
