import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fetch_official import URLS, collect, parse
from validate_candidates import validate

FIXTURES = Path(__file__).parent / 'fixtures'

def fixture(name):
    return BeautifulSoup((FIXTURES / name).read_bytes(), 'html.parser')

class RosterTests(unittest.TestCase):
    def test_house_fields_and_honorific(self):
        rows = parse('衆議院', fixture('house.html'), URLS['衆議院'])
        self.assertEqual(rows[0]['name'], '前川恵')
        self.assertEqual(rows[0]['party'], '自民')
        self.assertEqual(rows[0]['district'], '（比）北関東')
        self.assertEqual(len(rows), 2)

    def test_senate_rowspan_and_columns(self):
        rows = parse('参議院', fixture('senate.html'), 'https://www.sangiin.go.jp/japanese/joho1/kousei/giin/222/giin.htm')
        self.assertEqual([r['name'] for r in rows], ['青木愛', '青木一彦'])
        self.assertEqual(rows[0]['district'], '比例')
        self.assertEqual(rows[1]['district'], '鳥取・島根')
        self.assertEqual(validate(rows, 0)[0], [])

    def test_senate_redirect_keeps_actual_source(self):
        current = URLS['参議院']
        actual = current.replace('/current/', '/999/')
        calls = []
        def loader(url):
            calls.append(url)
            if url == current:
                return BeautifulSoup('<a href="../999/giin.htm">こちら</a>', 'html.parser')
            return fixture('senate.html')
        rows, counts = collect('参議院', current, loader)
        self.assertEqual(calls, [current, actual])
        self.assertEqual(rows[0]['sources'][0]['url'], actual)
        self.assertEqual(counts, {actual: 2})

    def test_external_redirect_rejected(self):
        with self.assertRaises(ValueError):
            collect('参議院', URLS['参議院'], lambda _: BeautifulSoup('<a href="https://example.com/giin.htm">こちら</a>', 'html.parser'))

    def test_partial_house_roster_rejected(self):
        with self.assertRaises(ValueError):
            collect('衆議院', URLS['衆議院'], lambda _: fixture('house.html'))

    def test_all_ten_house_pages_are_collected(self):
        base = URLS['衆議院'].rsplit('/', 1)[0] + '/'
        calls = []
        def loader(url):
            calls.append(url)
            page = int(url.rsplit('/', 1)[1].replace('giin.htm', ''))
            soup = fixture('house.html')
            for i, a in enumerate(soup.select('a[href]')):
                a['href'] = f'../../../../itdb_giinprof.nsf/html/profile/{page * 10 + i}.html'
            nav = BeautifulSoup(''.join(f'<a href="{i}giin.htm">行</a>' for i in range(1, 11)), 'html.parser')
            soup.append(nav)
            return soup
        rows, counts = collect('衆議院', URLS['衆議院'], loader)
        self.assertEqual(set(calls), {f'{base}{i}giin.htm' for i in range(1, 11)})
        self.assertEqual(len(calls), 10)
        self.assertEqual(len(rows), 20)
        self.assertEqual(len(counts), 10)

    def test_low_counts_still_fail_validation(self):
        rows = parse('衆議院', fixture('house.html'), URLS['衆議院'])
        self.assertTrue(validate(rows)[0])

if __name__ == '__main__':
    unittest.main()
