import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from build_review import normalize

def candidates():
    return [dict(name='確認用議員',house=house,kana='かくにん',district='比例',party='会派名',updated_at='2026-10-23',sources=[{'label':'一覧','url':f'https://{host}/list.htm'},{'label':'公式プロフィール','url':f'https://{host}/profile/{i}.htm'}]) for house,host in [('衆議院','www.shugiin.go.jp'),('参議院','www.sangiin.go.jp')] for i in range(100)]

class ReviewDataTests(unittest.TestCase):
    def test_group_is_not_inferred_as_party(self):
        source=candidates();original=copy.deepcopy(source)
        rows,counts=normalize(source)
        self.assertEqual(counts,{'衆議院':100,'参議院':100})
        self.assertIsNone(rows[0]['party'])
        self.assertEqual(rows[0]['parliamentary_group'],'会派名')
        self.assertEqual(source,original)
    def test_duplicate_profile_fails(self):
        rows=candidates();rows[1]['sources']=rows[0]['sources']
        with self.assertRaisesRegex(ValueError,'duplicate'):normalize(rows)
    def test_unofficial_source_fails(self):
        rows=candidates();rows[0]['sources'][0]['url']='https://example.org/list'
        with self.assertRaisesRegex(ValueError,'official source'):normalize(rows)
    def test_partial_snapshot_fails(self):
        with self.assertRaisesRegex(ValueError,'threshold'):normalize(candidates()[:100])

if __name__=='__main__':unittest.main()
