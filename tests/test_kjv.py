import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import import_kjv_archive
import import_web_archive
import compare_russyn_kjv


class KJVTests(unittest.TestCase):
    def test_kjv_usfm_nested_styles_and_note(self):
        raw = r'\nd \+w LORD|strong="H3068"\+w*\nd* \add was\add* good\f + \fr 1:1 \ft A note.\f*' + '\n' + r'\s1 A heading'
        text, notes, words = import_web_archive.render(raw, 'test')
        self.assertEqual(text, 'LORD was good')
        self.assertEqual(words[0]['strong'], 'H3068')
        self.assertIn('A note.', notes[0]['raw_usfm'])

    def test_reject_unknown_source(self):
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / 'other.zip'
            archive.write_bytes(b'not the reviewed archive')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                import_kjv_archive.import_archive(archive, Path(root) / 'out')
            self.assertFalse((Path(root) / 'out').exists())

    def test_mapping_exception_and_fingerprints(self):
        mapping = json.loads(compare_russyn_kjv.DEFAULT_MAP.read_text(encoding='utf-8'))
        pair = next(r for r in mapping['relationships'] if r['russyn'] == [{'book': 'ROM', 'chapter': 14, 'verse': 24}])
        self.assertEqual(pair['kjv'], [{'book': 'ROM', 'chapter': 16, 'verse': 25}])
        self.assertEqual(mapping['sources']['kjv']['archive_sha256'], import_kjv_archive.EXPECTED_SHA256)
        self.assertEqual(len(mapping['relationships']), 13)


if __name__ == '__main__':
    unittest.main()
