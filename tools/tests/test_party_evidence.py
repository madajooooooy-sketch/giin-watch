import copy
import datetime
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fetch_parties import match, extract
from build_review import apply_party_evidence

def member(name='伊藤孝恵',kana='いとうたかえ',house='参議院',id='one'):
    return dict(id=id,name=name,kana=kana,house=house,party=None)

class PartyTests(unittest.TestCase):
    def test_same_reading_does_not_override_exact_name(self):
        rows=[member(),member('伊藤孝江',id='two')]
        record=dict(source_name='伊藤 孝恵',source_kana='いとう たかえ',house='参議院',url='https://new-kokumin.jp/member/ito-takae')
        found,unmatched=match([record],rows,'国民民主党')
        self.assertEqual(found[0]['member_id'],'one');self.assertEqual(unmatched,[])
    def test_ambiguous_kana_is_not_assigned(self):
        rows=[member(),member('伊藤孝江',id='two')]
        record=dict(source_name='いとう孝恵',source_kana='いとうたかえ',house='参議院',url='https://new-kokumin.jp/member/')
        self.assertEqual(match([record],rows,'国民民主党')[0],[])
    def test_wrong_house_does_not_match(self):
        record=dict(source_name='伊藤孝恵',source_kana='いとうたかえ',house='衆議院',url='https://new-kokumin.jp/member/')
        self.assertEqual(match([record],[member()],'国民民主党')[0],[])
    def test_candidates_are_not_current_party_members(self):
        raw='[{"名前大":"確認用", "所属議会":"元参議院議員"}]'.encode()
        self.assertEqual(extract('sansei-new',raw,'https://sanseito.jp/member/'),[])
    def test_source_required_for_application(self):
        evidence=dict(member_id='one',party='国民民主党',url='https://example.com/',house='参議院',source_name='伊藤孝恵',source_kana='いとうたかえ',checked_at='2026-10-23T00:00:00+00:00')
        with self.assertRaisesRegex(ValueError,'Unapproved'):apply_party_evidence([member()],[evidence])
        evidence['url']='https://new-kokumin.jp/member/ito-takae'
        rows=apply_party_evidence([member()],[evidence]);self.assertEqual(rows[0]['party'],'国民民主党')
        self.assertEqual(rows[0]['party_sources'][0]['url'],evidence['url'])
    def test_other_note_accounts_are_rejected(self):
        e=dict(member_id='one',party='民主改革の会',url='https://note.com/other/n/test',house='衆議院',source_name='小川淳也',source_kana='おがわじゅんや',checked_at='2026-10-23T00:00:00+00:00')
        with self.assertRaisesRegex(ValueError,'account'):apply_party_evidence([member('小川淳也','おがわじゅんや','衆議院')],[e])

if __name__=='__main__':unittest.main()
