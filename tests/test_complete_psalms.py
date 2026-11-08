import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / 'scripts'))
import build_complete_psalm_map as builder
import compare_psalms


class CompletePsalmTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.ru = self.root / 'ru'; self.en = self.root / 'en'
        self.ru.mkdir(); self.en.mkdir()
        for path, sha in [(self.ru, builder.RUSSIAN_SHA256), (self.en, builder.KJV_SHA256)]:
            (path / 'manifest.json').write_text(json.dumps({'archive_sha256': sha, 'edition': path.name}))
        russian = {'book':'PSA','chapter_preambles':[{'chapter':86,'raw_usfm':r'\q1'}, {'chapter':89,'raw_usfm':r'\q1'}],
                   'verses':[{'chapter':86,'verse':1,'text':'Заголовок','notes':[]}, {'chapter':86,'verse':2,'text':'объединённый стих','notes':[]},
                             {'chapter':89,'verse':6,'text':'две части','notes':[]}]}
        kjv = {'book':'PSA','chapter_preambles':[{'chapter':87,'raw_usfm':r'\d A Heading'}],
               'verses':[{'chapter':87,'verse':i,'text':f'verse {i}','notes':[]} for i in (1,2)] +
                        [{'chapter':90,'verse':i,'text':f'verse {i}','notes':[]} for i in (5,6)]}
        (self.ru/'PSA.json').write_text(json.dumps(russian, ensure_ascii=False), encoding='utf-8')
        (self.en/'PSA.json').write_text(json.dumps(kjv), encoding='utf-8')
        rows = [{'russyn':{'chapter':c,'verse':v}, 'status':'unparsed_rule_review'} for c,v in [(86,1),(86,2),(89,6)]]
        self.report={'rows':rows, 'source':{'url':'source','license':'LGPL'}}
        self.pilot=self.root/'pilot.json';self.pilot.write_text(json.dumps({'sources':{'russyn':{'archive_sha256':builder.RUSSIAN_SHA256},'kjv':{'archive_sha256':builder.KJV_SHA256}},'relationships':[]}))

    def test_build_and_reverse_merged_verses(self):
        with patch.object(builder,'audit',return_value=self.report), patch.object(builder,'PILOT',self.pilot):
            mapping=builder.build(Path('source'),self.ru,self.en)
        self.assertEqual(mapping['verse_relationship_count'],3)
        self.assertEqual(mapping['omissions'],[])
        file=self.root/'map.json';file.write_text(json.dumps(mapping))
        result=compare_psalms.display(compare_psalms.compare('Psalm 87:1','kjv',self.ru,self.en,file))
        self.assertIn('Псалтирь 86:2',result)
        self.assertIn('Psalms 87:2',result)
        self.assertIn('edition_override',result)
        heading=compare_psalms.display(compare_psalms.compare('Псалом 86:1','russyn',self.ru,self.en,file))
        self.assertIn('Psalms 87:heading — A Heading',heading)
        merged=compare_psalms.display(compare_psalms.compare('Psalm 90:6','kjv',self.ru,self.en,file))
        self.assertIn('Псалтирь 89:6',merged)
        self.assertIn('Psalms 90:5',merged)

    def test_multi_line_heading_and_part_disclosure(self):
        book={'chapter_preambles':[{'chapter':10,'raw_usfm':'\\d Начальнику хора.\n\\m Псалом Давида.\n\\q1'}]}
        self.assertEqual(compare_psalms.read_location(book,{'chapter':10,'verse':0})[0], 'Начальнику хора. Псалом Давида.')
        self.assertEqual(compare_psalms.parse_ref('Psalm 51:0')['verse'],0)
        with self.assertRaises(ValueError):compare_psalms.parse_ref('John 3:16')

    def test_unresolved_heading_and_partial_heading_are_explicit(self):
        mapping = {'mapping_id':'test', 'kind':'complete_psalm_source_map',
                   'evidence':{'sha256':builder.CROSSWIRE_SHA256, 'url':'source'},
                   'sources':{'russyn':{'archive_sha256':builder.RUSSIAN_SHA256}, 'kjv':{'archive_sha256':builder.KJV_SHA256}},
                   'unresolved_russian_headings':[86],
                   'relationships':[{'russyn':[{'book':'PSA','chapter':86,'verse':1}],
                                     'kjv':[{'book':'PSA','chapter':87,'verse':0,'part':'a'}],
                                     'status':'source_mapped', 'evidence':{'line':1,'rule':'test rule'}}]}
        ru = json.loads((self.ru/'PSA.json').read_text(encoding='utf-8'))
        ru['chapter_preambles'][0]['raw_usfm'] = r'\d Заголовок'
        (self.ru/'PSA.json').write_text(json.dumps(ru, ensure_ascii=False), encoding='utf-8')
        file=self.root/'map.json'; file.write_text(json.dumps(mapping))
        part=compare_psalms.display(compare_psalms.compare('Псалом 86:1','russyn',self.ru,self.en,file))
        self.assertIn('part(s) a', part)
        self.assertIn('full heading shown', part)
        unresolved=compare_psalms.display(compare_psalms.compare('Псалом 86:0','russyn',self.ru,self.en,file))
        self.assertIn('No established corresponding location', unresolved)

    def test_reject_unsupported_map_and_missing_target(self):
        with patch.object(builder,'audit',return_value=self.report), patch.object(builder,'PILOT',self.pilot):
            data=json.loads((self.en/'PSA.json').read_text());data['verses'].pop();(self.en/'PSA.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'Unmapped KJV locations'):
                builder.build(Path('source'),self.ru,self.en)


if __name__ == '__main__': unittest.main()
