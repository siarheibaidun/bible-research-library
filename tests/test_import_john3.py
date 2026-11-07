import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('import_john3', Path(__file__).parents[1] / 'scripts' / 'import_john3.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ImportTests(unittest.TestCase):
    def test_full_chapter_and_note(self):
        verse = r'\wj “\+w God|strong="G2316"\+w* loves”\wj*\f + \fr 3:16 \ft A note.\f*'
        data = '\\id JHN Test\n\\c 3\n' + ''.join(f'\\v {n} {verse}\n' for n in range(1, 37)) + '\\c 4\n'
        out = module.parse(data.encode(), 'sample.usfm')
        record = out['verses'][15]
        self.assertEqual(record['text'], '“God loves”')
        self.assertEqual(record['footnotes'][0]['text'], 'A note.')
        self.assertEqual(record['strong_annotations'][0]['strong'], 'G2316')
        self.assertIn('\\f ', record['raw_usfm'])

    def test_rejects_wrong_book_and_incomplete_chapter(self):
        with self.assertRaises(ValueError):
            module.parse(b'\\id MAT\n\\c 3\n\\v 1 text', 'x')
        with self.assertRaises(ValueError):
            module.parse(b'\\id JHN\n\\c 3\n\\v 1 text', 'x')


if __name__ == '__main__':
    unittest.main()
