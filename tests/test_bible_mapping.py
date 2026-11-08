import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import build_bible_source_map as builder
import compare_bible


class BibleMappingTests(unittest.TestCase):
    def test_cross_chapter_and_partial_range(self):
        index={'NUM':[(12,15),(12,16),(13,1),(13,2)], '1KI':[(18,33),(18,34)]}
        r=builder.expand('Num.12.16-Num.13.2',index)
        self.assertEqual([(x['chapter'],x['verse']) for x in r],[(12,16),(13,1),(13,2)])
        r=builder.expand('1Kgs.18.33!b-1Kgs.18.34',index)
        self.assertEqual(r[0]['part'],'b')
        with self.assertRaises(ValueError):builder.expand('Num.13.9-Num.13.10',index)

    def test_edition_corrections_and_source_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); rules=root/'rules';rules.write_text('# no explicit rules\n')
            pilot=root/'pilot';pilot.write_text(json.dumps({'sources':{'russyn':{'archive_sha256':builder.RUSSIAN_SHA256},'kjv':{'archive_sha256':builder.KJV_SHA256}},'relationships':[]}))
            ru={'PRO':[(4,28),(13,14),(13,15)],'ACT':[(19,40)],'3JN':[(1,14),(1,15)]}
            en={'PRO':[(13,14)],'ACT':[(19,40),(19,41)],'3JN':[(1,14)]}
            with patch.object(builder,'BOOKS',['PRO','ACT','3JN']), patch.object(builder,'PILOT',pilot), \
                 patch.object(builder,'CROSSWIRE_SHA256',hashlib.sha256(rules.read_bytes()).hexdigest()), \
                 patch.object(builder,'load_index',side_effect=[ru,en]):
                result=builder.build(rules,root/'ru',root/'en')
            pairs={(r['russyn'][0]['book'],r['russyn'][0]['chapter'],r['russyn'][0]['verse']):r for r in result['relationships']}
            self.assertEqual(pairs['PRO',4,28]['kjv'],[])
            self.assertEqual(pairs['PRO',13,14]['status'],'no_numbered_counterpart')
            self.assertEqual(pairs['PRO',13,15]['kjv'],[builder.ref('PRO',13,14)])
            self.assertEqual(pairs['ACT',19,40]['kjv'],[builder.ref('ACT',19,40),builder.ref('ACT',19,41)])
            self.assertEqual(pairs['3JN',1,15]['kjv'],[builder.ref('3JN',1,14,'b')])
            self.assertEqual(result['uncovered_kjv'],[])

    def test_display_many_to_one_and_no_counterpart(self):
        mapping={'mapping_id':'test','evidence':{'url':'source'}}
        manifests={'russyn':{'archive_sha256':'r','edition':'ru'},'kjv':{'archive_sha256':'k','edition':'en'}}
        books={'russyn':{(1,14):{'text':'first','notes':[]},(1,15):{'text':'second','notes':[]}},
               'kjv':{(1,14):{'text':'combined','notes':[]}}}
        def r(v, part):return {'russyn':[builder.ref('3JN',1,v)],'kjv':[builder.ref('3JN',1,14,part)],'status':'edition_override','evidence':'checked'}
        text=compare_bible.display((mapping,manifests,books,[r(14,'a'),r(15,'b')]))
        self.assertIn('3 Иоанна 1:15',text)
        self.assertIn('part(s) a, b',text)
        self.assertIn('not been individually text-verified',text)
        only={'russyn':[builder.ref('3JN',1,14)],'kjv':[],'status':'no_numbered_counterpart','evidence':'none'}
        text=compare_bible.display((mapping,manifests,books,[only]))
        self.assertIn('No directly corresponding numbered verse',text)


if __name__=='__main__':unittest.main()
