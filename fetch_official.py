#!/usr/bin/env python3
"""Fetch public Diet member lists into review-only candidates; never publish automatically."""
import argparse, datetime, json, re, sys, urllib.request
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
URLS={
 '衆議院':'https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu/7giin.htm',
 '参議院':'https://www.sangiin.go.jp/japanese/joho1/kousei/giin/current/giin.htm'
}
def clean(s):return re.sub(r'\s+','',s or '').replace('君','')
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'GiinWatchResearch/0.8 (public information; weekly fetch)','Accept':'text/html'})
 with urllib.request.urlopen(req,timeout=25) as r:
  raw=r.read(4_000_000); encoding=r.headers.get_content_charset() or ('shift_jis' if 'shugiin' in url else 'utf-8')
 return BeautifulSoup(raw.decode(encoding,errors='replace'),'html.parser')
def parse(house,soup,url):
 out=[]
 for tr in soup.select('tr'):
  cells=tr.find_all(['td','th'],recursive=False)
  vals=[c.get_text(' ',strip=True) for c in cells]
  if len(vals)<4:continue
  # Different official pages use optional kana/row headings; locate a linked name.
  linked=[(i,c.find('a',href=True)) for i,c in enumerate(cells)]
  linked=[(i,a) for i,a in linked if a and clean(a.get_text(' ',strip=True)) and not any(x in a.get_text(' ',strip=True) for x in ('正字','トップ','一覧'))]
  if not linked:continue
  i,a=linked[0]; name=clean(a.get_text(' ',strip=True)).split('［')[0].split('[')[0]
  if not 2<=len(name)<=18 or any(x in name for x in ('議員','氏名','会派','選挙区','あ行','か行')):continue
  tail=[v.strip() for v in vals[i+1:]]
  if house=='衆議院':
   # expected: name, kana, parliamentary group, district, elections
   if len(tail)<3:continue
   kana,group,district=tail[:3]
  else:
   # expected: name, kana, parliamentary group, district, term
   if len(tail)<3:continue
   kana,group,district=tail[:3]
  if not group or not district:continue
  from urllib.parse import urljoin
  out.append({'name':name,'house':house,'party':group,'district':district,'kana':kana,'sources':[{'label':'公式議員一覧','url':url},{'label':'議員プロフィール','url':urljoin(url,a['href'])}], 'updated_at':datetime.date.today().isoformat()})
 return list({(m['house'],m['name'],m['district']):m for m in out}.values())
def main():
 p=argparse.ArgumentParser();p.add_argument('--min-house',type=int,default=100);a=p.parse_args()
 candidates=[];errors=[];stats={}
 for house,url in URLS.items():
  try:
   rows=parse(house,fetch(url),url);stats[house]=len(rows);candidates+=rows
   if len(rows)<a.min_house:errors.append(f'{house}: {len(rows)} records, below review threshold {a.min_house}')
  except Exception as e:errors.append(f'{house}: {type(e).__name__}: {e}')
 out=ROOT/'reports';out.mkdir(exist_ok=True)
 (out/'candidates.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'fetch-report.json').write_text(json.dumps({'fetched_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'counts':stats,'errors':errors,'source_urls':URLS,'status':'REVIEW_REQUIRED'},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'counts':stats,'errors':errors,'output':str(out/'candidates.json')},ensure_ascii=False))
 return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
