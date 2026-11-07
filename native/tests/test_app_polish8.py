"""APP-POLISH-008: the offline session's equipment records and the demo outfits with pre-draw effects.

Portable: the character list's item values FILE[@GROUP:INDEX[:LEVEL[:OPTION[:EXT]]]] (mu_charsel_parse_item):
file-only values load as before (no record), records are range-checked; the bundled demo characters carry a record
for every item (Ironclad's sword the Cookery Short Sword 0:68 = 0x0b2a, +9 excellent); the character store writes
the records and reads them back; the Lorencia demo players' new items are pre-draw types (gen_item_owner_fx
PRE_FX_TYPES) and none is wing 0x2384/0x2385 (OBJECT-owned particles, still refused).

Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): every bundled record names its own model in Item.bmd (mu-data);
`mu-walk --hero-item` with Ironclad's items: the hero's slots take the records' types, levels and options (the
hero_records line) and the level / excellent passes are drawn; a file-only sword keeps the file's first record.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
sys.path.insert(0, str(ROOT/'scripts'))
from gen_item_owner_fx import PRE_FX_TYPES  # noqa: E402

CLIENT_DIR = NATIVE/'client'
PLAYERS = NATIVE/'world/lorencia-demo-players.txt'
WALK = NATIVE/'build/mu-walk'
DATA = NATIVE/'build/mu-data'
GAME = os.environ.get('MU_GAME_ROOT')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and GAME
LIBS = ['-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation'] \
    if sys.platform == 'darwin' else []
SLOTS = {'helm': 1, 'armor': 2, 'pants': 3, 'gloves': 4, 'boots': 5, 'weapon0': 6, 'weapon1': 7, 'wing': 8}


def demo_items():
    """(name, slot, file, record) for every item of the bundled demo characters."""
    out = []
    for line in (CLIENT_DIR/'demo-characters.txt').read_text().splitlines():
        line = line.split('#', 1)[0].split()
        for token in line[4:]:
            key, value = token.split('=', 1)
            file, _, record = value.partition('@')
            out.append((line[3], key, file, tuple(int(v, 0) for v in record.split(':')) if record else None))
    return out


class Host(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.host = cls.dir/'app-polish8-host'
        subprocess.run(['make', '-C', str(NATIVE), 'build/libmunative.a'], check=True, capture_output=True)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(NATIVE),
                        str(NATIVE/'tests/app_polish8_host.c'), str(CLIENT_DIR/'offline-session.c'),
                        str(NATIVE/'build/libmunative.a'), *LIBS, '-lm', '-o', str(cls.host)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def call(self, *args):
        p = subprocess.run([str(self.host), *map(str, args)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_item_values(self):
        cases = {
            'Item/Sword04.bmd': ('/g/Data/Item/Sword04.bmd', 0, 0, 0, 0, 0),
            '/abs/Sword04.bmd': ('/abs/Sword04.bmd', 0, 0, 0, 0, 0),
            'Item/CookriShortSword.bmd@0:68': ('/g/Data/Item/CookriShortSword.bmd', 1, 68, 0, 0, 0),
            'Item/CookriShortSword.bmd@0:68:9:1': ('/g/Data/Item/CookriShortSword.bmd', 1, 68, 9, 1, 0),
            'Item/Wing09.bmd@12:37:15:1:0xff': ('/g/Data/Item/Wing09.bmd', 1, 12*512 + 37, 15, 1, 255),
            'Item/x.bmd@15:511:0:0:0': ('/g/Data/Item/x.bmd', 1, 15*512 + 511, 0, 0, 0),
        }
        for value, want in cases.items():
            with self.subTest(value=value):
                r = self.call('item', value, '/g')
                self.assertEqual((r['path'], r['set'], r['code'], r['level'], r['option'], r['ext']), want)
        for value in ('', '@0:1', 'a.bmd@', 'a.bmd@0', 'a.bmd@16:0', 'a.bmd@0:512', 'a.bmd@0:1:16', 'a.bmd@0:1:0:2',
                      'a.bmd@0:1:0:0:256', 'a.bmd@0:1:0:0:0:0', 'a.bmd@-1:1', 'a.bmd@0:1x', 'a.bmd@0:1:'):
            with self.subTest(value=value):
                self.assertEqual(self.call('item', value, '/g'), {'error': 1})

    def test_bundled_characters_carry_records(self):
        rows = self.call('session', CLIENT_DIR/'demo-session.txt', '/g')['characters']
        self.assertEqual([r['name'] for r in rows], ['Nightfall', 'Ironclad', 'Windleaf', 'Spellblade', 'Crownlord'])
        for row in rows:
            for item in row['items'].values():
                self.assertEqual(item['set'], 1, row['name'])
        ironclad = rows[1]['items']
        self.assertEqual(ironclad['6'], {'path': '/g/Data/Item/CookriShortSword.bmd', 'set': 1, 'code': 68,
                                         'level': 9, 'option': 1, 'ext': 0})   # model type 0x0b2a
        self.assertEqual((ironclad['7']['code'], ironclad['7']['level']), (6*512, 7))
        self.assertEqual((ironclad['8']['code'], ironclad['8']['level']), (12*512 + 1, 0))
        self.assertTrue(all(i[3] and 0 <= (i[3][2] if len(i[3]) > 2 else 0) <= 9 for i in demo_items()))   # modest

    def test_file_only_lists_load_unchanged(self):
        listing = self.dir/'old-characters.txt'
        listing.write_text('1 0x01 400 Ironclad weapon0=Item/Sword04.bmd weapon1=Item/Shield01.bmd\n')
        session = self.dir/'old-session.txt'
        session.write_text(f'characters {listing}\n')
        items = self.call('session', session, '/g')['characters'][0]['items']
        self.assertEqual(items['6'], {'path': '/g/Data/Item/Sword04.bmd', 'set': 0, 'code': 0, 'level': 0,
                                      'option': 0, 'ext': 0})
        self.assertEqual(items['7']['set'], 0)
        listing.write_text('1 0x01 400 Ironclad weapon0=Item/Sword04.bmd@0:3:16\n')
        self.assertIn('needs FILE[@GROUP:INDEX', self.call('session', session, '/g')['error'])

    def test_store_keeps_the_records(self):
        store = self.dir/'store.txt'
        rows = self.call('session', CLIENT_DIR/'demo-session.txt', '/g', store)['characters']
        self.assertEqual(rows, self.call('session', CLIENT_DIR/'demo-session.txt', '/g')['characters'])
        self.assertIn('weapon0=Item/CookriShortSword.bmd@0:68:9:1:0', store.read_text())


class DemoPlayers(unittest.TestCase):
    def test_new_outfits_are_pre_draw_types(self):
        wearing = {}
        for line in PLAYERS.read_text().splitlines():
            if not line.startswith('player '):
                continue
            name = line.split()[1]
            for key, value in re.findall(r'\b(helm|armor|pants|gloves|boots|weapon0|weapon1|wing)=(\S+)', line):
                g, i = (int(v) for v in value.split(':')[:2])
                wearing.setdefault(name, []).append(0xae6 + g*512 + i)
        pre = {n: [t for t in types if t in PRE_FX_TYPES] for n, types in wearing.items()}
        self.assertEqual(pre, {'Aeris': [0x1748], 'Kyra': [], 'Redhand': [0x0b4c, 0x230b], 'Mordred': [],
                               'Sunwing': [0x2311], 'Shopkeep': [], 'Nomad': [], 'Corvin': [0x0f1c]})
        self.assertFalse({0x2384, 0x2385} & {t for types in wearing.values() for t in types})


def walk(*args, players=None, frames=60):
    with tempfile.TemporaryDirectory() as tmp:
        extra = ['--players', str(players), '--player-range', '20'] if players else ['--no-players']
        result = subprocess.run([str(WALK), '--game-root', GAME, '--headless', '--backend', 'soft', '--no-audio',
                                 '--width', '320', '--height', '240', '--every', '1000', '--out-dir', tmp,
                                 '--tile', '128,124', '--frames', str(frames), '--quiet', *extra, *args],
                                capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    pre = next((r for r in rows if r.get('item_pre_draw') is True), None)
    records = next((r for r in rows if r.get('hero_records') is True), None)
    return pre, records


@unittest.skipUnless(PRIVATE, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class PrivateRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-walk', 'build/mu-data'], check=True, capture_output=True)

    def item(self, code):
        p = subprocess.run([str(DATA), 'item', str(Path(GAME, 'Data/Local/Item.bmd')), str(code)],
                           capture_output=True, text=True, check=True)
        return json.loads(p.stdout.splitlines()[0])

    def test_records_name_their_own_models(self):
        for name, slot, file, record in demo_items():
            with self.subTest(name=name, slot=slot):
                row = self.item(record[0]*512 + record[1])
                self.assertEqual(row['file'].lower(), Path(file).name.lower())
        # the file's first record is the [Bound] variant 0:65 (0x0b27): the code picks 0:68 (0x0b2a)
        self.assertEqual(self.item(65)['file'], 'CookriShortSword.bmd')
        self.assertTrue(self.item(65)['name'].startswith('[Bound]'))
        self.assertFalse(self.item(68)['name'].startswith('[Bound]'))

    def ironclad(self, sword):
        items = {slot: f'{file}@{":".join(map(str, record))}' for name, slot, file, record in demo_items()
                 if name == 'Ironclad'}
        items['weapon0'] = sword or items['weapon0']
        return [a for slot, value in items.items() for a in ('--hero-item', f'{slot}={value}')]

    def test_hero_slots_take_the_records(self):
        pre, records = walk(*self.ironclad(None))
        slots = {s['item']: s for s in records['slots']}
        self.assertEqual([(s['type'], s['level'], s['option'], s['ext']) for s in records['slots']],
                         [(0x0b2a, 9, 1, 0), (0x16e6, 7, 0, 0), (0x22e7, 0, 0, 0)])
        self.assertEqual(pre['hero'], {'pre_effects': 8, 'pre_refused': 0, 'hidden': 0})
        # the level glow and the excellent pass add passes over the same sword at level 0
        _, plain = walk(*self.ironclad('Item/CookriShortSword.bmd@0:68'))
        plain = {s['item']: s for s in plain['slots']}
        self.assertEqual(plain[6]['type'], 0x0b2a)
        self.assertGreater(slots[6]['passes'], plain[6]['passes'])

    def test_file_only_sword_keeps_the_first_record(self):
        pre, records = walk(*self.ironclad('Item/CookriShortSword.bmd'))
        self.assertNotIn(6, [s['item'] for s in records['slots']])   # no record: the file's 0x0b27 at level 0
        self.assertEqual(pre['hero'], {'pre_effects': 8, 'pre_refused': 0, 'hidden': 0})

    def test_no_record_keeps_the_report(self):
        pre, records = walk('--hero-item', 'weapon0=Item/Sword04.bmd', '--hero-item', 'wing=Item/Wing02.bmd')
        self.assertIsNone(records)
        self.assertIsNone(pre)


if __name__ == '__main__':
    unittest.main()
