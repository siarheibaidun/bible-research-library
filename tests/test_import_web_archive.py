import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('web', Path(__file__).parents[1] / 'scripts' / 'import_web_archive.py')
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


class ImportTest(unittest.TestCase):
    def test_notes_words_and_poetry(self):
        raw = '\\q1 \\w God|strong="G2316"\\w* loves\\f + \\fr 1:1 \\ft Note.\\f*\\x + \\xo 1:1 \\xt Gen 1:1\\x*'
        text, notes, words = web.render(raw, 'test')
        self.assertEqual(text, 'God loves')
        self.assertEqual([n['type'] for n in notes], ['footnote', 'cross_reference'])
        self.assertEqual(words, [{'text': 'God', 'strong': 'G2316'}])
        self.assertIn('\\ft Note.', notes[0]['raw_usfm'])

    def test_note_only_verse_is_preserved(self):
        data = b'\\id LUK\n\\c 1\n\\v 1 \\f + \\fr 1:1 \\ft Omitted text.\\f*\n'
        verse = web.parse_book(data, 'test')['verses'][0]
        self.assertEqual(verse['text'], '')
        self.assertEqual(len(verse['notes']), 1)

    def test_refuses_unknown_marker_and_missing_verse(self):
        with self.assertRaises(ValueError):
            web.render('text \\unknown value', 'test')
        with self.assertRaises(ValueError):
            web.parse_book(b'\\id JHN\n\\c 1\n\\v 2 text', 'test')

    def test_heading_excluded_but_preserved_in_raw(self):
        raw = '\\w text|strong="H1"\\w*\n\\d A heading\n'
        text, _, _ = web.render(raw, 'test')
        self.assertEqual(text, 'text')
        self.assertIn('A heading', raw)


if __name__ == '__main__':
    unittest.main()
