import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('audit', Path(__file__).parents[1] / 'scripts' / 'audit_psalm_mapping.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PsalmAuditTests(unittest.TestCase):
    def test_rule_shapes_and_zero(self):
        pairs = audit.parse_rule('Ps.3.1-Ps.3.3=Ps.3.0-Ps.3.2')
        self.assertEqual([(s['verse'], t[0]['verse']) for s, t in pairs], [(1, 0), (2, 1), (3, 2)])
        self.assertEqual(len(audit.parse_rule('Ps.22.1=Ps.23.0-Ps.23.1')[0][1]), 2)
        with self.assertRaises(ValueError):
            audit.parse_rule('Ps.89.1-Ps.89.17=Ps.90.0-Ps.90.17')
        with self.assertRaises(ValueError):
            audit.parse_rule('Ps.12.6=Ps.13.5-Ps.12.6')

    def test_audit_does_not_guess_or_approve_candidates(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); ru = root / 'ru'; en = root / 'en'; ru.mkdir(); en.mkdir()
            for path, digest in [(ru, 'ru'), (en, 'en')]:
                (path / 'manifest.json').write_text(json.dumps({'archive_sha256': digest}))
            def v(c, n, text): return {'chapter': c, 'verse': n, 'text': text}
            (ru / 'PSA.json').write_text(json.dumps({'book': 'PSA', 'verses': [v(3,1,'title'),v(3,2,'text'),v(12,6,'unparsed'),v(1,1,'no rule')]}))
            (en / 'PSA.json').write_text(json.dumps({'book': 'PSA', 'verses': [v(3,1,'text')], 'chapter_preambles': [{'chapter':3,'raw_usfm':r'\d Heading'}]}))
            source = root / 'rules'; source.write_text('Ps.3.1-Ps.3.2=Ps.3.0-Ps.3.1\nPs.12.6=Ps.13.5-Ps.12.6\n')
            import hashlib
            with patch.object(audit, 'CROSSWIRE_SHA256', hashlib.sha256(source.read_bytes()).hexdigest()), patch.object(audit, 'RUSSIAN_SHA256', 'ru'), patch.object(audit, 'KJV_SHA256', 'en'):
                report = audit.audit(source, ru, en)
                rows={(r['russyn']['chapter'], r['russyn']['verse']): r for r in report['rows']}
                self.assertEqual(rows[3,1]['status'], 'heading_or_part_review')
                self.assertIn('Heading', rows[3,1]['target_details'][0]['source_usfm'])
                self.assertEqual(rows[3,2]['status'], 'candidate_text_review')
                self.assertEqual(rows[12,6]['status'], 'unparsed_rule_review')
                self.assertEqual(rows[1,1]['status'], 'no_explicit_rule')
                self.assertEqual(report['status'], 'review_only')
                (en / 'manifest.json').write_text(json.dumps({'archive_sha256': 'other'}))
                with self.assertRaisesRegex(ValueError, 'checksum'):
                    audit.audit(source, ru, en)


if __name__ == '__main__':
    unittest.main()
