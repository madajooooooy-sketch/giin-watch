#!/usr/bin/env python3
"""Build a separate review snapshot without touching published member data."""
import argparse
import datetime
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from fetch_parties import norm, SOURCES

ROOT = Path(__file__).resolve().parents[1]

def normalize(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError('Candidates must be a non-empty array')
    result, seen = [], set()
    counts = {'衆議院': 0, '参議院': 0}
    for index, row in enumerate(rows):
        house = row.get('house')
        if house not in counts:
            raise ValueError(f'row {index}: invalid house')
        for key in ('name', 'district', 'kana', 'party', 'updated_at'):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ValueError(f'row {index}: missing {key}')
        datetime.date.fromisoformat(row['updated_at'])
        sources = row.get('sources', [])
        host = 'www.shugiin.go.jp' if house == '衆議院' else 'www.sangiin.go.jp'
        if len(sources) != 2:
            raise ValueError(f'row {index}: expected list and profile sources')
        for source in sources:
            url = urlparse(source.get('url', ''))
            if url.scheme != 'https' or url.netloc != host:
                raise ValueError(f'row {index}: invalid official source')
        profile = sources[1]['url']
        if not re.search(r'/profile/\d+\.html?$', profile):
            raise ValueError(f'row {index}: invalid profile')
        if profile in seen:
            raise ValueError(f'row {index}: duplicate profile')
        seen.add(profile)
        result.append({
            'id': profile, 'name': row['name'], 'kana': row['kana'],
            'house': house, 'district': row['district'],
            'parliamentary_group': row['party'], 'party': None,
            'party_status': '未確認', 'review_status': '公式名簿から取得・個別確認前',
            'retrieved_on': row['updated_at'], 'sources': sources,
        })
        counts[house] += 1
    for house, count in counts.items():
        if count < 100:
            raise ValueError(f'{house}: {count} below review threshold 100')
    return result, counts

def apply_party_evidence(rows, evidence):
    known={r['id']:r for r in rows};seen=set()
    allowed={(party,urlparse(catalog).netloc) for _,party,_,catalog in SOURCES}
    for item in evidence:
        member_id=item['member_id']
        if member_id in seen:raise ValueError('Duplicate party evidence')
        seen.add(member_id)
        if member_id not in known:continue  # Old evidence never adds departed members.
        row=known[member_id];party=item['party'];url=urlparse(item['url'])
        if url.scheme!='https' or (party,url.netloc) not in allowed:raise ValueError('Unapproved party source')
        if party=='民主改革の会' and not url.path.startswith('/drp_japan2026/'):raise ValueError('Unapproved party account')
        if item['house']!=row['house']:raise ValueError('Party evidence house mismatch')
        if norm(item['source_name'])!=norm(row['name']):
            peers=[r for r in rows if r['house']==row['house'] and norm(r['kana'])==norm(item['source_kana'])]
            if not norm(item['source_kana']) or len(peers)!=1 or peers[0]['id']!=member_id:raise ValueError('Ambiguous party evidence identity')
        checked=datetime.datetime.fromisoformat(item['checked_at'])
        if checked.tzinfo is None:raise ValueError('Party check time must have a timezone')
        row.update(party=party,party_status='政党公式出典で確認',party_checked_at=item['checked_at'],party_sources=[{'label':party+'公式議員情報','url':item['url']}])
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidates', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'review')
    parser.add_argument('--party-evidence',type=Path,default=ROOT/'review/party-evidence.json')
    args = parser.parse_args()
    rows, counts = normalize(json.loads(args.candidates.read_text(encoding='utf-8')))
    if args.party_evidence.exists():
        apply_party_evidence(rows,json.loads(args.party_evidence.read_text(encoding='utf-8')))
    report = {
        'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'counts': counts, 'total': len(rows), 'unique_profiles': len(rows),
        'official_sources_valid': True, 'party_unconfirmed': sum(r['party'] is None for r in rows),
        'party_confirmed': sum(r['party'] is not None for r in rows),
        'review_status': 'REVIEW_REQUIRED',
        'notes': ['会派と政党は別の項目。政党は公式出典で確認できたものだけ掲載しています。',
                  '取得日は公式名簿の掲載基準日や個別確認日を意味しません。',
                  '人数は取得時点の掲載数です。全議席の充足を保証しません。'],
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for filename, payload in [('members-review.json', rows), ('quality-report.json', report)]:
        (args.output / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    main()
