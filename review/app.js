'use strict';
const $ = id => document.getElementById(id);
const normalize = value => String(value ?? '').normalize('NFKC').replace(/[\u30a1-\u30f6]/g, c => String.fromCharCode(c.charCodeAt(0)-0x60)).replace(/\s+/g, '').toLowerCase();
const PAGE_SIZE = 24;
let members = [], filtered = [], page = 1;
const collator = new Intl.Collator('ja');
function el(tag, text, className) { const node=document.createElement(tag); if(text!==undefined)node.textContent=text; if(className)node.className=className; return node; }
function officialLink(source) { const u=new URL(source.url); if(u.protocol!=='https:'||!['www.shugiin.go.jp','www.sangiin.go.jp'].includes(u.hostname))throw Error('公式出典のURLを確認してください'); const a=el('a',source.label+' ↗'); a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';return a; }
function applyFilters() {
  const terms=normalize($('query').value).split(/[、,]/).filter(Boolean);
  filtered=members.filter(m=>(!$('house').value||m.house===$('house').value)&&(!$('group').value||m.parliamentary_group===$('group').value)&&terms.every(t=>normalize([m.name,m.kana,m.house,m.district,m.parliamentary_group].join(' ')).includes(t)));
  const field=$('sort').value==='district'?'district':'kana';
  filtered.sort((a,b)=>collator.compare(normalize(a[field]),normalize(b[field]))||collator.compare(a.name,b.name));page=1;render();
}
function render() {
  $('status').textContent=`${filtered.length.toLocaleString('ja-JP')}人が該当 / ${members.length.toLocaleString('ja-JP')}人`;
  $('export').disabled=!filtered.length;
  const pages=Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));page=Math.min(page,pages);
  const fragment=document.createDocumentFragment();
  for(const m of filtered.slice((page-1)*PAGE_SIZE,page*PAGE_SIZE)) {
    const card=el('article',undefined,'member'),top=el('div',undefined,'member-top');
    top.append(el('span',m.house,'house'+(m.house==='参議院'?' upper':'')),el('span',m.parliamentary_group,'group'));
    card.append(top,el('h3',m.name),el('p',m.kana,'kana'),el('p',m.district,'district'));
    const button=el('button','詳細・出典を見る');button.type='button';button.setAttribute('aria-label',m.name+'の詳細・出典を見る');button.onclick=()=>showDetail(m);card.append(button);fragment.append(card);
  }
  if(!filtered.length)fragment.append(el('p','該当する議員がいません。検索語や絞り込み条件を変更してください。','empty'));
  $('results').replaceChildren(fragment);$('pageLabel').textContent=`${page} / ${pages} ページ`;$('prev').disabled=page===1;$('next').disabled=page===pages;
}
function showDetail(m) {
  const body=$('detailBody'),heading=el('h2',m.name);heading.id='detailName';body.replaceChildren(heading,el('p',m.kana,'kana'));
  const dl=el('dl');for(const [label,value] of [['議院',m.house],['選挙区',m.district],['会派',m.parliamentary_group],['政党','未確認'],['取得日',m.retrieved_on],['確認状態',m.review_status]])dl.append(el('dt',label),el('dd',value));
  const links=el('div',undefined,'source-links');m.sources.forEach(s=>links.append(officialLink(s)));
  body.append(dl,links,el('p','会派の表記は取得時点の公式名簿に基づきます。最新の所属・氏名表記は公式プロフィールでご確認ください。活動実績、公約、政治資金は未取得です。','note'));
  $('detail').showModal();$('closeDetail').focus();
}
function csvCell(value) {let text=String(value??'');if(/^[=+\-@\t\r]/.test(text))text="'"+text;return '"'+text.replace(/"/g,'""')+'"';}
function exportCSV() {
  const rows=[['氏名','ふりがな','議院','選挙区','会派','政党','取得日','確認状態','公式一覧','公式プロフィール'],...filtered.map(m=>[m.name,m.kana,m.house,m.district,m.parliamentary_group,'未確認',m.retrieved_on,m.review_status,m.sources[0].url,m.sources[1].url])];
  const blob=new Blob(['\uFEFF'+rows.map(r=>r.map(csvCell).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download='議員候補_検索結果.csv';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function load() {
  $('error').hidden=true;$('status').textContent='読み込み中…';
  try {
    const response=await fetch('members-review.json');if(!response.ok)throw Error('HTTP '+response.status);const data=await response.json();
    if(!Array.isArray(data)||!data.length||data.some(m=>!m.name||!m.kana||!['衆議院','参議院'].includes(m.house)||!m.parliamentary_group||!m.district||m.party!==null||!m.retrieved_on||!Array.isArray(m.sources)||m.sources.length!==2))throw Error('名簿形式が不正です');
    data.forEach(m=>m.sources.forEach(officialLink));members=data;
    const groups=[...new Set(members.map(m=>m.parliamentary_group))].sort(collator.compare);$('group').replaceChildren(new Option('すべての会派',''),...groups.map(g=>new Option(g,g)));
    for(const [id,house] of [['total',null],['lower','衆議院'],['upper','参議院']])$(id).textContent=(house?members.filter(m=>m.house===house).length:members.length).toLocaleString('ja-JP');
    const dates=[...new Set(members.map(m=>m.retrieved_on))].sort();$('snapshot').textContent=`取得日 ${dates.join(' / ')} · 出典：衆議院・参議院公式サイト`;
    applyFilters();
  } catch(error) {members=[];filtered=[];$('results').replaceChildren();$('error').hidden=false;$('status').textContent='読み込みに失敗しました';$('snapshot').textContent='取得情報を読み込めませんでした';$('export').disabled=true;$('prev').disabled=true;$('next').disabled=true;$('pageLabel').textContent='';}
}
$('filters').onsubmit=e=>e.preventDefault();['query','house','group','sort'].forEach(id=>$(id).addEventListener('input',applyFilters));
$('reset').onclick=()=>{$('filters').reset();applyFilters();$('query').focus();};$('export').onclick=exportCSV;$('retry').onclick=load;$('closeDetail').onclick=()=>$('detail').close();
for(const [id,step] of [['prev',-1],['next',1]])$(id).onclick=()=>{page+=step;render();$('results').focus();};
load();
