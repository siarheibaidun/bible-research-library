import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import build_psalm_source_map as builder
import compare_russyn_kjv as compare


class SourceMappingTests(unittest.TestCase):
    def test_builder_keeps_ambiguous_and_pilot_out(self):
        def row(v, target, status='candidate_text_review'):
            return {'russyn': {'chapter': 3, 'verse': v}, 'status': status,
                    'target_details': [{'chapter': 3, 'verse': target}],
                    'candidates': [{'rule': 'rule', 'line': 1, 'targets': [{'chapter': 3, 'verse': target}]}]}
        report = {'source': {'url': 'pinned', 'license': 'LGPL'}, 'rows': [row(1, 1), row(2, 2), row(3, 2), row(4, 4)],
                  'unparsed_rules': [], 'source_references_not_in_dataset': [], 'reverse_coverage': {}}
        pilot = {'sources': {'russyn': {'archive_sha256': builder.RUSSIAN_SHA256}, 'kjv': {'archive_sha256': builder.KJV_SHA256}},
                 'relationships': [{'russyn': [{'book':'PSA','chapter':3,'verse':4}], 'kjv': [{'book':'PSA','chapter':3,'verse':4}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'pilot.json'; p.write_text(json.dumps(pilot))
            with patch.object(builder, 'audit', return_value=report):
                result, summary = builder.build(Path('ignored'), Path('ru'), Path('kjv'), p)
        self.assertEqual(len(result['relationships']), 1)
        self.assertEqual(result['relationships'][0]['status'], 'source_mapped')
        self.assertEqual(summary['source_verses'], summary['source_mapped'] + sum(summary['excluded_for_review'].values()))
        self.assertEqual(summary['excluded_for_review']['target_multiple_rules_review'], 2)
        self.assertEqual(summary['excluded_for_review']['reserved_for_checked_pilot'], 1)

    def test_compare_labels_candidates_and_keeps_pilot_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ru=root/'ru';en=root/'en';ru.mkdir();en.mkdir()
            hashes={'russyn':'ru','kjv':'en'}
            for directory, digest in [(ru,'ru'),(en,'en')]:
                (directory/'manifest.json').write_text(json.dumps({'archive_sha256':digest, 'edition':'test'}))
                (directory/'PSA.json').write_text(json.dumps({'book':'PSA','verses':[{'chapter':3,'verse':1,'text':'text','notes':[]}]}))
            r={'book':'PSA','chapter':3,'verse':1}
            sources={k:{'archive_sha256':v} for k,v in hashes.items()}
            pilot={'mapping_id':'pilot','sources':sources,'relationships':[]}
            p=root/'pilot.json';p.write_text(json.dumps(pilot))
            candidate={'mapping_id':'candidate','kind':'source_mapped_candidates','sources':sources,
                'pilot_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'evidence':{'sha256':'76385bbd47834482c651e509e898d704cf27b5d4037ecff26ec7baf45f1edba6','name':'CrossWire','url':'source'},
                'relationships':[{'russyn':[r],'kjv':[r],'status':'source_mapped','source_rule':'rule','source_line':3}]}
            c=root/'candidate.json';c.write_text(json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,'No available mapping'):
                compare.compare('Psalm 3:1','kjv',ru,en,p)
            result=compare.format_comparison(compare.compare('Psalm 3:1','kjv',ru,en,p,c))
            self.assertIn('not been individually verified',result)
            self.assertIn('CrossWire, line 3: rule',result)
            candidate['pilot_sha256']='bad';c.write_text(json.dumps(candidate))
            with self.assertRaisesRegex(ValueError,'different pilot'):
                compare.compare('Psalm 3:1','kjv',ru,en,p,c)

    def test_two_verified_multi_verse_relationships(self):
        p=Path(__file__).parents[1]/'data'/'versification'/'russyn_kjv_pilot.json'
        data=json.loads(p.read_text(encoding='utf-8'))
        for chapter, target in [(12,13),(89,90)]:
            pair=next(x for x in data['relationships'] if x['russyn']==[{'book':'PSA','chapter':chapter,'verse':6}])
            self.assertEqual(pair['kjv'],[{'book':'PSA','chapter':target,'verse':5},{'book':'PSA','chapter':target,'verse':6}])


if __name__=='__main__': unittest.main()
