#!/usr/bin/env python3
"""Match official party rosters to Diet profiles; generate review-only evidence."""
import argparse
import datetime
import hashlib
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
 ('jimin','自由民主党','https://www.jimin.jp/member/data/member.json','https://www.jimin.jp/member/search/'),
 ('ishin-shu','日本維新の会','https://o-ishin.jp/member/shugiin/','https://o-ishin.jp/member/shugiin/'),
 ('ishin-san','日本維新の会','https://o-ishin.jp/member/sangiin/','https://o-ishin.jp/member/sangiin/'),
 ('kokumin','国民民主党','https://new-kokumin.jp/member','https://new-kokumin.jp/member'),
 ('jcp','日本共産党','https://www.jcp.or.jp/diet_member/','https://www.jcp.or.jp/diet_member/'),
 ('mirai','チームみらい','https://team-mir.ai/about','https://team-mir.ai/about'),
 ('sansei-new','参政党','https://sanseito.jp/nppoj/wp-content/themes/wp_310/member_for_newpage.json','https://sanseito.jp/member/'),
 ('sansei-data','参政党','https://sanseito.jp/2020/wp-content/themes/twentynineteen/member.json','https://sanseito.jp/member/'),
 ('drp-members','民主改革の会','https://note.com/drp_japan2026/n/na56baf0ab77f','https://note.com/drp_japan2026/n/na56baf0ab77f'),
]

def norm(text):
    text=unicodedata.normalize('NFKC',text or '')
    text=''.join(chr(ord(c)-0x60) if '\u30a1'<=c<='\u30f6' else c for c in text)
    return re.sub(r'[\s・･]','',text)

def extract(key,raw,url):
    out=[]
    def add(name,kana,house,profile=None):
        if house not in ('衆議院','参議院') or not name:return
        out.append(dict(source_name=name,source_kana=kana,house=house,url=urljoin(url,profile) if profile else url))
    if key=='jimin':
        for r in json.loads(raw):
            house=r.get('parliament','').replace('議員','')
            add(r.get('lastName','')+r.get('firstName',''),r.get('lastNameKana','')+r.get('firstNameKana',''),house,r['url'])
    elif key.startswith('sansei'):
        data=json.loads(raw)
        if isinstance(data,dict):data=data.get('candidate_posts',[])
        for r in data:
            council=r.get('所属議会','')
            # Candidates and former office holders are never treated as members.
            house='衆議院' if council.startswith('衆議院議員') else '参議院' if council.startswith('参議院議員') else ''
            add(r.get('名前大',''),r.get('名前小',''),house)
    else:
        soup=BeautifulSoup(raw,'html.parser')
        if key.startswith('ishin'):
            house='衆議院' if key.endswith('shu') else '参議院'
            for dl in soup.select('dl'):
                dt=dl.find('dt');kind=dl.select_one('.member_label02, .member_label03')
                if not dt or not kind or house not in kind.get_text():continue
                kana=dt.find('span');a=dl.parent.find('a',href=True)
                add(''.join(str(t) for t in dt.find_all(string=True,recursive=False)),kana.get_text() if kana else '',house,a['href'] if a else None)
        elif key=='kokumin':
            for section in soup.select('section.member_sec'):
                h=section.find('h3');house='衆議院' if h and '衆議院' in h.get_text() else '参議院' if h and '参議院' in h.get_text() else ''
                for dl in section.select('dl.profile'):
                    a=dl.select_one('.name a');kana=dl.select_one('.kana')
                    if a:add(a.get_text(),kana.get_text() if kana else '',house,a['href'])
        elif key=='jcp':
            for sec in soup.select('section[id^="giin_"]'):
                name=sec.select_one('.name');kana=sec.select_one('.furigana');house=sec.select_one('.housetype .type')
                if name and house:add(name.get_text(),kana.get_text() if kana else '',house.get_text(strip=True),url+'#'+sec['id'])
        elif key=='mirai':
            for card in soup.select('.member-card'):
                name=card.select_one('.name');title=card.select_one('.title');link=card.select_one('a.detail-button')
                if not name or not title:continue
                kana=''.join(rt.get_text() for rt in name.select('rt'))
                for rt in name.select('rt'):rt.decompose()
                add(name.get_text(),kana,title.get_text(strip=True).replace('議員',''),link['href'] if link else None)
        elif key=='drp-members':
            article=soup.select_one('#note-article')
            if article:
                for h in article.select('h2'):
                    m=re.fullmatch(r'(.+?)（([ぁ-ゖー・]+)）',h.get_text(strip=True))
                    if m:add(m[1],m[2],'衆議院',url+('#'+h['id'] if h.get('id') else ''))
    return out

def match(records,members,party):
    evidence=[];unmatched=[]
    for record in records:
        candidates=[m for m in members if m['house']==record['house'] and norm(m['name'])==norm(record['source_name'])]
        if not candidates:
            candidates=[m for m in members if m['house']==record['house'] and len(norm(record['source_kana']))>=4 and norm(m['kana'])==norm(record['source_kana'])]
        if len(candidates)!=1:
            unmatched.append(record);continue
        m=candidates[0]
        method='氏名・議院一致' if norm(m['name'])==norm(record['source_name']) else 'ふりがな・議院の一意一致'
        evidence.append(dict(member_id=m['id'],party=party,match_method=method,**record))
    return evidence,unmatched

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--members',type=Path,default=ROOT/'review/members-review.json')
    parser.add_argument('--cache',type=Path)
    parser.add_argument('--candidates',type=Path,help='Fresh official candidates for new/retired member detection')
    parser.add_argument('--output',type=Path,default=ROOT/'reports')
    args=parser.parse_args();members=json.loads(args.members.read_text(encoding='utf-8'))
    published={m['id']:m for m in members}
    if args.candidates:
        from build_review import normalize
        members,_=normalize(json.loads(args.candidates.read_text(encoding='utf-8')))
    checked=datetime.datetime.now(datetime.timezone.utc).isoformat();found={};conflicts=set();errors=[];stats=[]
    for key,party,url,catalog in SOURCES:
        try:
            if args.cache:
                path=args.cache/(key+('.json' if key=='jimin' or key.startswith('sansei') else '.html'));raw=path.read_bytes()
            else:
                req=urllib.request.Request(url,headers={'User-Agent':'GiinWatchResearch/1.0 (public party roster verification)'})
                with urllib.request.urlopen(req,timeout=25) as response:raw=response.read(5_000_001)
                if len(raw)>5_000_000:raise ValueError('Source exceeds size limit')
            records=extract(key,raw,url);matched,unmatched=match(records,members,party)
            if not records:raise ValueError('No official member entries found')
            digest=hashlib.sha256(raw).hexdigest()
            stats.append(dict(party=party,catalog_url=catalog,data_url=url,source_sha256=digest,extracted=len(records),matched=len(matched),unmatched=[r['source_name'] for r in unmatched]))
            for e in matched:
                e.update(checked_at=checked,catalog_url=catalog,data_url=url,source_sha256=digest)
                previous=found.get(e['member_id'])
                if previous and previous['party']!=e['party']:conflicts.add(e['member_id'])
                elif not previous:found[e['member_id']]=e
        except Exception as exc:errors.append(dict(party=party,url=url,error=str(exc)))
    for member_id in conflicts:found.pop(member_id,None)
    evidence=list(found.values());baseline={m['id']:published.get(m['id'],{}).get('party') for m in members}
    changes=[dict(member_id=e['member_id'],before=baseline[e['member_id']],after=e['party'],url=e['url']) for e in evidence if baseline[e['member_id']]!=e['party']]
    report=dict(checked_at=checked,status='REVIEW_REQUIRED',confirmed=len(evidence),unconfirmed=len(members)-len(evidence),by_party=dict(Counter(e['party'] for e in evidence)),source_results=stats,errors=errors,conflicts=sorted(conflicts),changes=changes,
        new_member_ids=sorted(set(m['id'] for m in members)-set(published)),
        missing_member_ids=sorted(set(published)-set(m['id'] for m in members)),
        not_reconfirmed=[m['id'] for m in members if baseline[m['id']] and m['id'] not in found],
        note='未一致・取得失敗は離党の根拠ではありません。新しい政党の出典はSOURCESに登録して再取得します。公開データを自動変更しません。')
    args.output.mkdir(parents=True,exist_ok=True)
    for filename,value in [('party-evidence.json',evidence),('party-change-report.json',report)]:
        (args.output/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('confirmed','unconfirmed','by_party','errors','conflicts')},ensure_ascii=False))
    return bool(errors or conflicts)

if __name__=='__main__':raise SystemExit(main())
