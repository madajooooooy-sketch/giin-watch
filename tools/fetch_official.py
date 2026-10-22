#!/usr/bin/env python3
"""Fetch public Diet member lists into review-only candidates; never publish automatically."""
import argparse, datetime, json, re, sys, urllib.request
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
URLS={
 '衆議院':'https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/syu/7giin.htm',
 '参議院':'https://www.sangiin.go.jp/japanese/joho1/kousei/giin/current/giin.htm'
}
def clean(s):return re.sub(r'\s+','',s or '')
def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'GiinWatchResearch/0.8 (public information; weekly fetch)','Accept':'text/html'})
 with urllib.request.urlopen(req,timeout=25) as r:
  raw=r.read(4_000_001)
  if len(raw)>4_000_000:raise ValueError('Official page exceeds size limit')
  encoding=r.headers.get_content_charset()
 # Let the HTML charset declaration choose Shift_JIS or UTF-8.
 return BeautifulSoup(raw,'html.parser',from_encoding=encoding)

def collect(house,url,loader=fetch):
 """Follow only official roster links, retaining the actual source page."""
 soup=loader(url); pages={url:soup}
 if house=='衆議院':
  for a in soup.select('a[href]'):
   target=urljoin(url,a['href'])
   if (urlparse(target).netloc==urlparse(url).netloc
       and re.fullmatch(r'(?:[1-9]|10)giin\.htm',target.rsplit('/',1)[-1])
       and target.rsplit('/',1)[0]==url.rsplit('/',1)[0]):
    pages.setdefault(target,None)
  if len(pages)!=10:raise ValueError('Expected all 10 House roster pages')
 else:
  # current/giin.htm uses an HTML refresh, not an HTTP redirect.
  for _ in range(3):
   if soup.select('a[href*="/profile/"]'):break
   targets={urljoin(url,a['href']) for a in soup.select('a[href]')}
   targets={t for t in targets if urlparse(t).netloc=='www.sangiin.go.jp'
            and re.fullmatch(r'/japanese/joho1/kousei/giin/\d+/giin\.htm',urlparse(t).path)}
   if len(targets)!=1:raise ValueError('Cannot identify Senate roster redirect')
   url=targets.pop();soup=loader(url)
  else:raise ValueError('Too many Senate roster redirects')
  pages={url:soup}
 rows=[];counts={}
 for source,page in pages.items():
  if page is None:page=loader(source)
  parsed=parse(house,page,source)
  if not parsed:raise ValueError(f'No member records on {source}')
  counts[source]=len(parsed);rows.extend(parsed)
 keys=[(r['house'],r['sources'][1]['url']) for r in rows]
 if len(keys)!=len(set(keys)):raise ValueError('Duplicate member profiles across roster pages')
 return rows,counts

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
  i,a=linked[0]
  profile=urljoin(url,a['href'])
  pattern=r'/internet/itdb_giinprof\.nsf/html/profile/\d+\.html' if house=='衆議院' else r'/japanese/joho1/kousei/giin/profile/\d+\.htm'
  if urlparse(profile).netloc!=urlparse(url).netloc or not re.fullmatch(pattern,urlparse(profile).path):continue
  name=clean(a.get_text(' ',strip=True)).split('［')[0].split('[')[0]
  if house=='衆議院':name=name.removesuffix('君')
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
  out.append({'name':name,'house':house,'party':group,'district':district,'kana':kana,'sources':[{'label':'公式議員一覧','url':url},{'label':'議員プロフィール','url':urljoin(url,a['href'])}], 'updated_at':datetime.date.today().isoformat()})
 return out
def main():
 p=argparse.ArgumentParser();p.add_argument('--min-house',type=int,default=100);a=p.parse_args()
 candidates=[];errors=[];stats={};page_counts={}
 for house,url in URLS.items():
  try:
   rows,pages=collect(house,url);page_counts[house]=pages;stats[house]=len(rows);candidates+=rows
   if len(rows)<a.min_house:errors.append(f'{house}: {len(rows)} records, below review threshold {a.min_house}')
  except Exception as e:errors.append(f'{house}: {type(e).__name__}: {e}')
 out=ROOT/'reports';out.mkdir(exist_ok=True)
 (out/'candidates.json').write_text(json.dumps(candidates,ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'fetch-report.json').write_text(json.dumps({'fetched_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'counts':stats,'page_counts':page_counts,'errors':errors,'source_urls':URLS,'status':'REVIEW_REQUIRED'},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'counts':stats,'errors':errors,'output':str(out/'candidates.json')},ensure_ascii=False))
 return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
