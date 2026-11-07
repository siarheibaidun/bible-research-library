import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('lookup', Path(__file__).parents[1] / 'scripts' / 'lookup_verse.py')
lookup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lookup)


class LookupTests(unittest.TestCase):
    def test_references(self):
        self.assertEqual(lookup.parse_reference('John 3:16'), ('JHN', 3, 16))
        self.assertEqual(lookup.parse_reference('1 John 4:8'), ('1JN', 4, 8))
        self.assertEqual(lookup.parse_reference('jhn 3:16'), ('JHN', 3, 16))
        for ref in ('John 0:16', 'Unknown 3:1', 'John 3', '../JHN 3:16'):
            with self.assertRaises(ValueError):
                lookup.parse_reference(ref)

    def test_lookup_and_note(self):
        with tempfile.TemporaryDirectory() as path:
            directory = Path(path)
            (directory / 'manifest.json').write_text(json.dumps({'edition': 'WEB', 'archive_sha256': 'abc'}))
            (directory / 'JHN.json').write_text(json.dumps({'book': 'JHN', 'source_file': 'john.usfm', 'verses': [
                {'chapter': 3, 'verse': 16, 'text': 'Verse text.', 'notes': [
                    {'type': 'footnote', 'raw_usfm': r'\f + \fr 3:16 \ft The \+wh λέξη\+wh* here.\f*'}]}]}))
            result = lookup.format_result(lookup.lookup(directory, 'John 3:16'))
            self.assertIn('Verse text.', result)
            self.assertIn('Footnote (3:16): The λέξη here.', result)
            self.assertIn('Archive SHA-256: abc', result)
            with self.assertRaises(ValueError):
                lookup.lookup(directory, 'John 3:17')

    def test_unknown_note_format_keeps_raw(self):
        self.assertIsNone(lookup.read_note(r'\f unexpected\f*'))


if __name__ == '__main__':
    unittest.main()
