"""APP-POLISH-005: the offline demo's ground skill through the session's skill list, hotkeys and join stats.

Portable: the offline session's `skills` / `hero` lines, the fixture lines they become, and the join data reaching
the session (synthetic skill tables).  Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NATIVE_DATA_DIR with
lang/ and converted gfx/, MU_GFX_LIB): mu-client with the bundled session selects Windleaf, hotkey 2 selects 2044,
a right-click casts it through the client's checks, and the report counts the rain, rings, decals and sounds.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_session_support import NATIVE, SCENARIOS, run_tool

CLIENT_DIR = NATIVE / 'client'
TABLES = SCENARIOS / 'skills-tables'
LIBS = ['-framework', 'CoreText', '-framework', 'CoreGraphics', '-framework', 'CoreFoundation'] \
    if sys.platform == 'darwin' else []


def start_stats():
    """START[16][5] of the progress fixture (its DEMO class start stats)."""
    text = (NATIVE / 'fixture/behaviors/progress.c').read_text()
    body = text[text.index('START[16][5] = {'):]
    body = body[:body.index('};')]
    return [tuple(int(v) for v in row.split(',')) for row in re.findall(r'\{([-\d, ]+)\}', body)]


class Host(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.host = cls.dir / 'app-polish5-host'
        subprocess.run(['make', '-C', str(NATIVE), 'build/libmunative.a', 'build/mu-session'], check=True,
                       capture_output=True)
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-I', str(NATIVE),
                        str(NATIVE / 'tests/app_polish5_host.c'), str(CLIENT_DIR / 'offline-session.c'),
                        str(NATIVE / 'build/libmunative.a'), *LIBS, '-lm', '-o', str(cls.host)],
                       check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def session(self, path):
        p = subprocess.run([str(self.host), 'session', str(path), '/nonexistent'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def lines(self, cls, file='', level=0, stats=(0, 0, 0, 0, 0), points=0, root='/root'):
        p = subprocess.run([str(self.host), 'lines', str(cls), file, str(level), *map(str, stats), str(points), root],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout

    def test_bundled_profile_is_the_fixture_rule_at_the_list_level(self):
        row = self.session(CLIENT_DIR / 'demo-session.txt')
        self.assertTrue(row['skills'].endswith('/demo-skills.txt'), row)
        self.assertTrue(Path(row['skills']).is_file())
        self.assertEqual(len(row['heroes']), 1)
        hero = row['heroes'][0]
        self.assertEqual((hero['slot'], hero['class'], hero['level'], hero['world'], hero['tile']),
                         (2, 2, 320, 0, [182, 128]))
        self.assertEqual((hero['stats'], hero['points']), ([22, 1302, 20, 15, 0], 318))
        self.assertEqual(row['missing'], 1)
        # every number from the fixture's own DEMO rules: the Elf start stats, five points per level
        start = start_stats()[2]
        spent = sum(s - b for s, b in zip(hero['stats'], start))
        self.assertTrue(all(s >= b for s, b in zip(hero['stats'], start)))
        self.assertEqual(spent + hero['points'], 5 * (hero['level'] - 1))
        # the skills file: the Elf learns 2044 and keeps Triple Shot; hotkey 1 Triple Shot, hotkey 2 the ground skill
        text = (CLIENT_DIR / 'demo-skills.txt').read_text().splitlines()
        lists = [l.split() for l in text if l.startswith('list ')]
        keys = [l.split() for l in text if l.startswith('keys ')]
        self.assertEqual([l[1] for l in lists], ['2'])
        self.assertIn('2044', lists[0][2:])
        self.assertIn('24', lists[0][2:])
        self.assertEqual(keys[0][1:4], ['2', '24', '2044'])
        self.assertEqual(len(keys[0]) - 2, 10)

    def test_hero_lines_are_checked(self):
        cases = {
            'hero 2 str=1 agi=2 vit=3 ene=4 cmd=5': None,
            'hero 2 str=1 agi=2 vit=3 ene=4 cmd=5 points=6': None,
            'hero 2 str=1 agi=2 vit=3 ene=4': 'expected hero',                     # every stat once
            'hero 2 str=1 agi=2 vit=3 ene=4 cmd=5 str=6': 'expected hero',
            'hero 2 str=1 agi=70000 vit=3 ene=4 cmd=5': 'expected hero',            # 16-bit fields
            'hero 2 str=1 agi=-1 vit=3 ene=4 cmd=5': 'expected hero',
            'hero 12 str=1 agi=2 vit=3 ene=4 cmd=5': 'expected hero',               # slots 0..9
            'hero 2 str=1 agi=2 vit=3 ene=4 cmd=5 luck=1': 'expected hero',
            'hero 2 str=1 agi=2x vit=3 ene=4 cmd=5': 'expected hero',
            'hero 2 str=1 agi=2 vit=3 ene=4 cmd=5\nhero 2 str=1 agi=2 vit=3 ene=4 cmd=5': 'expected hero',
        }
        for i, (line, error) in enumerate(cases.items()):
            with self.subTest(line=line):
                path = self.dir / f'hero{i}.txt'
                path.write_text(line + '\n')
                row = self.session(path)
                if error:
                    self.assertIn(error, row.get('error', ''))
                else:
                    self.assertNotIn('error', row)
                    self.assertEqual(row['heroes'][0]['stats'], [1, 2, 3, 4, 5])
                    self.assertEqual(row['heroes'][0]['points'], 6 if 'points' in line else 0)
        path = self.dir / 'sub' / 'session.txt'
        path.parent.mkdir(exist_ok=True)
        path.write_text('skills my skills.txt   \n')
        self.assertEqual(self.session(path)['skills'], str(path.parent / 'my skills.txt'))

    def test_lines_without_profile_are_the_previous_lines(self):
        self.assertEqual(self.lines(1), 'use skills\nat 1 skills root /root\nat 1 skills login 1 30\n'
                         'use progress class=1 latency=0\nat 1 progress join\n'
                         'at 1 progress respawn map=0 x=182 y=128 dir=3\n')
        text = self.lines(2, '/a b/demo-skills.txt', 320, (22, 1302, 20, 15, 0), 318)
        self.assertEqual(text.splitlines()[2], 'at 1 skills file /a b/demo-skills.txt')
        self.assertEqual(text.splitlines()[4], 'use progress class=2 latency=0 level=320 points=318 str=22 agi=1302 '
                                               'vit=20 ene=15 cmd=0')

    def test_join_data_reaches_the_session(self):
        tables = self.dir / 'tables'
        shutil.copytree(TABLES, tables)
        # synthetic records for the two skills of the file (index, requirement, class map and weapon column only)
        with open(tables / 'skills.tsv', 'a') as f:
            f.write('24\tSynthetic Shot\t0\t0\t5\t0\t6\t0\t0\t0\t0\t0\t0\t6\t0\t0\t0\t24\t0\t0\n'
                    '2044\tSynthetic Rain\t160\t0\t19\t8\t7\t0\t0\t1302\t0\t0\t0\t6\t14\t0\t0\t7\t0\t0\n')
        with open(tables / 'skills_class.tsv', 'a') as f:
            for skill in (24, 2044):
                f.write(f'{skill}\t0\t0\t1' + '\t0' * 16 + '\n')
        with open(tables / 'skills_ext.tsv', 'a') as f:
            f.write('24' + '\t0' * 16 + '\t1\t110\t0\t0\n' + '2044' + '\t0' * 16 + '\t5\t110\t0\t0\n')
        for name, file, level, stats, expect in [
                ('profile', str(CLIENT_DIR / 'demo-skills.txt'), 320, (22, 1302, 20, 15, 0),
                 {'hero.agility': 1302, 'hero.strength': 22, 'skills.count': 14, 'skills.learned.2044': 1,
                  'skills.learned.24': 1}),
                ('built-in', '', 0, (0, 0, 0, 0, 0),
                 {'hero.agility': 25, 'hero.strength': 22, 'skills.learned.2044': 0, 'skills.learned.24': 1})]:
            with self.subTest(name=name):
                lines = self.lines(2, file, level, stats, 318 if level else 0, str(tables))
                lines = lines.replace('use skills\n', f'use skills\nat 1 skills data {tables}\n')
                scn = self.dir / f'{name}.scn'
                scn.write_text('endpoint game 127.0.0.1:55905\n'
                               'join world=0 tile=182,128 class=2 level=320 name=Synthetic slot=2\n'
                               f'at 1 client skill-data {tables}\n' + lines +
                               ''.join(f'expect {k} = {v}\n' for k, v in expect.items()) +
                               'expect unbound = 0\nexpect undecodable = 0\n')
                p, rows = run_tool('fixture', scn, '--ticks', 6)
                self.assertEqual(p.returncode, 0, p.stdout[-2000:] + p.stderr)
                checks = [r for r in rows if 'expect' in r]
                self.assertEqual(len(checks), len(expect) + 2)
                self.assertTrue(all(r['pass'] for r in checks), checks)


GAME = os.environ.get('MU_GAME_ROOT')
DATA = os.environ.get('MU_NATIVE_DATA_DIR')
GFX = os.environ.get('MU_GFX_LIB')
PRIVATE = (os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and GAME and DATA and GFX and
           Path(DATA, 'lang/skills.tsv').is_file() and Path(DATA, 'gfx').is_dir() and Path(GFX).is_file())
FLOW = ('8:click:group:0 16:click:server:0 22:text:demo 24:tab 25:text:secret 28:enter 42:click:row:2 '
        '54:dblclick:row:2 100:key:0x32 109:move:845,100 110:rdown:845,100 111:rup:845,100')


@unittest.skipUnless(PRIVATE, 'private: MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NATIVE_DATA_DIR, MU_GFX_LIB')
class PrivateGroundSkill(unittest.TestCase):
    def run_client(self, session, folder):
        subprocess.run(['make', '-C', str(NATIVE), 'client'], check=True, capture_output=True)
        world = NATIVE / 'world'
        env = {**os.environ, 'MU_LANG_DIR': str(Path(DATA, 'lang')), 'MU_GFX_LIB': GFX}
        p = subprocess.run([str(NATIVE / 'build/mu-client'), '--game-root', GAME, '--session', str(session),
                            '--width', '1504', '--height', '936', '--placement', str(world / 'lorencia-demo-placement.txt'),
                            '--npc', '--npc-demo', str(world / 'lorencia-demo-npc.txt'), '--combat', '--progress',
                            '--items', '--players', str(world / 'lorencia-demo-players.txt'),
                            '--world-objects', str(Path(DATA, 'objects')), '--gfx', str(Path(DATA, 'gfx')),
                            '--no-audio', '--headless', '--backend', 'gl', '--frames', '170', '--every', '1000',
                            '--out-dir', str(folder), '--no-store', '--script', FLOW],
                           capture_output=True, text=True, env=env, timeout=300)
        if p.returncode and 'headless GL' in p.stderr:
            self.skipTest('no offscreen GL context')
        self.assertEqual(p.returncode, 0, p.stderr[-2000:])
        rows = [json.loads(l) for l in p.stdout.splitlines() if l.startswith('{')]
        summary = next(r for r in rows if r.get('summary') is True)
        effects = next(r for r in rows if r.get('effects') is True)
        return summary, effects, p.stderr

    def test_hotkey_and_right_click_cast_the_ground_skill(self):
        with tempfile.TemporaryDirectory() as folder:
            summary, effects, err = self.run_client(CLIENT_DIR / 'demo-session.txt', folder)
        self.assertEqual((summary['hero_slot'], summary['hero_class'], summary['world']), (2, 2, 0))
        self.assertRegex(err, r'skill 2044 at actor \d+: ok')
        self.assertEqual((effects['skills'], effects['max_live_0x70a']), (1, 1))
        self.assertGreater(effects['max_live_0x70c'], 0)
        self.assertGreater(effects['max_live_rings'], 0)
        self.assertGreater(effects['decals'], 0)
        self.assertGreater(effects['sounds'], 0)

    def test_without_the_join_stats_the_client_refuses_it(self):
        with tempfile.TemporaryDirectory() as folder:
            session = Path(folder, 'session.txt')
            text = (CLIENT_DIR / 'demo-session.txt').read_text()
            text = '\n'.join(l for l in text.splitlines() if not l.startswith('hero '))
            for name in ('demo-servers.txt', 'demo-characters.txt', 'demo-skills.txt'):
                text = text.replace(f' {name}', f' {CLIENT_DIR / name}')
            session.write_text(text + '\n')
            summary, effects, err = self.run_client(session, folder)
        self.assertEqual(summary['hero_slot'], 2)
        self.assertRegex(err, r'skill 2044 at actor \d+: requirements')
        self.assertEqual((effects['skills'], effects['max_live_0x70a'], effects['decals']), (0, 0, 0))


if __name__ == '__main__':
    unittest.main()
