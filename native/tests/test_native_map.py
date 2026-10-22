"""Maps and travel in the native session (NATIVE-MAP-001) checks.

Portable (synthetic data only): two synthetic worlds (Data/World1 and Data/World2,
the NATIVE-WORLD-001 open-ground fixture), a synthetic Lang plaintext directory
(gates.tsv, moves.tsv, globaltext.txt in the NATIVE-LANG-001 format) and
`mu-walk` (headless, software rasterizer):
  * a move request (--travel-script F:move:KEY) is answered by the demo server:
    the world changes with the existing loader, the hero lands inside the target
    gate's rectangle, the zen cost is taken;
  * a hero standing on an entrance gate tile triggers the client's gate test and
    travels to the target gate's world;
  * the server refuses a move below the record's level (no travel);
  * the move window's rows follow the client's rules (level, cost, the strife text);
  * --no-map turns the session off.
Private (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_LANG_DIR): Lorencia -> Noria -> Lorencia
with the installed data and the live-read tables.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
sys.path.insert(0, str(HERE))
from test_native_world import write_open_world  # noqa: E402

WALK = NATIVE / 'build/mu-walk'
PRIVATE = (os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT')
           and os.environ.get('MU_LANG_DIR'))

GATES = ('#index\tflag\tworld\tx1\ty1\tx2\ty2\ttarget\tdir\tmin_level\tmax_level\n'
         '1\t1\t0\t120\t60\t122\t61\t2\t0\t20\t-1\n'      # entrance in world 0 -> gate 2
         '2\t2\t1\t40\t40\t44\t42\t0\t3\t0\t-1\n'         # arrival area in world 1
         '3\t2\t0\t128\t128\t130\t130\t0\t1\t0\t-1\n')    # arrival area in world 0
MOVES = ('#index\tname\tserver_name\tid\tzen\tmin_level\tmax_level\tgate\tx44\tx48\tx4c\n'
         '1\tHome\tHome\t0\t1000\t1\t-1\t3\t0\t0\t-1\n'
         '2\tFar Land\tFarLand\t1\t2500\t10\t-1\t2\t1\t1\t-1\n'
         '42\tPeak\tPeak\t2\t3000\t5000\t-1\t2\t2\t2\t-1\n')
TEXT = '0\tGulim\n484\t - Welcome\n2987\t(Battle)\n'


def write_lang(directory):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'gates.tsv').write_text(GATES)
    (directory / 'moves.tsv').write_text(MOVES)
    (directory / 'globaltext.txt').write_text(TEXT)


def second_world(root):
    """Data/World2 (world 1): the World1 fixture with its files renamed."""
    src, dst = Path(root) / 'Data' / 'World1', Path(root) / 'Data' / 'World2'
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        shutil.copy(f, dst / f.name.replace('EncTerrain1', 'EncTerrain2'))


def walk(root, lang, *args):
    env = dict(os.environ, MU_LANG_DIR=str(lang))
    result = subprocess.run([str(WALK), '--game-root', str(root), '--headless', '--backend', 'soft', *[str(a) for a in args]],
                            capture_output=True, text=True, env=env)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    summary = next(r for r in rows if r.get('summary'))
    maps = [r for r in rows if r.get('map')]
    return summary, maps[0] if maps else None, rows, result


@unittest.skipUnless(WALK.exists(), 'mu-walk not built (make -C native)')
class SyntheticTravel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name) / 'game'
        write_open_world(cls.root)
        second_world(cls.root)
        cls.lang = Path(cls.tmp.name) / 'lang'
        write_lang(cls.lang)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_move_request_changes_world(self):
        summary, m, _, result = walk(self.root, self.lang, '--tile', '80,80', '--frames', '12',
                                     '--travel-script', '3:move:2')
        self.assertEqual(summary['world'], 1, result.stderr)
        self.assertEqual(summary['folder'], 2)
        self.assertEqual(m['travels'], 1)
        self.assertTrue(40 <= m['tile'][0] <= 44 and 40 <= m['tile'][1] <= 42, m)
        self.assertEqual(m['zen'], 10000000 - 2500)
        self.assertIn('travel: world 0 -> 1', result.stderr)

    def test_move_back_home(self):
        summary, m, _, _ = walk(self.root, self.lang, '--tile', '80,80', '--frames', '20',
                                '--travel-script', '3:move:2 10:move:1')
        self.assertEqual(summary['world'], 0)
        self.assertEqual(m['travels'], 2)
        self.assertTrue(128 <= m['tile'][0] <= 130 and 128 <= m['tile'][1] <= 130, m)
        self.assertEqual(m['zen'], 10000000 - 3500)

    def test_gate_entrance(self):
        summary, m, _, result = walk(self.root, self.lang, '--tile', '121,60', '--frames', '8')
        self.assertEqual(summary['world'], 1, result.stderr)
        self.assertIn('gate 1 -> 2', result.stderr)
        self.assertTrue(40 <= m['tile'][0] <= 44 and 40 <= m['tile'][1] <= 42, m)

    def test_level_refusal(self):
        summary, m, _, result = walk(self.root, self.lang, '--tile', '80,80', '--frames', '8',
                                     '--travel-script', '2:move:42')
        self.assertEqual(summary['world'], 0)
        self.assertEqual(m['travels'], 0)
        self.assertIn('refused', result.stderr)

    def test_rows(self):
        _, _, rows, _ = walk(self.root, self.lang, '--tile', '80,80', '--frames', '4', '--travel-script', '1:rows')
        moves = [r for r in rows if 'move_row' in r]
        self.assertEqual([r['map'] for r in moves], ['Home', 'Far Land', 'Peak'])   # record id order
        self.assertEqual([r['zen'] for r in moves], ['1000', '2500', '3000'])
        self.assertEqual([r['disabled'] for r in moves], [0, 0, 1])                  # level 1600 < 5000
        self.assertEqual([r['strife'] for r in moves], [0, 0, 1])                    # key 42: the strife flag

    def test_no_map(self):
        _, m, _, _ = walk(self.root, self.lang, '--tile', '121,60', '--frames', '4', '--no-map')
        self.assertIsNone(m)


@unittest.skipUnless(PRIVATE and WALK.exists(), 'private data (MU_RECOVERY_INTEGRATION, MU_GAME_ROOT, MU_LANG_DIR)')
class PrivateTravel(unittest.TestCase):
    def test_lorencia_noria_lorencia(self):
        root, lang = Path(os.environ['MU_GAME_ROOT']), Path(os.environ['MU_LANG_DIR'])
        summary, m, _, result = walk(root, lang, '--tile', '130,130', '--frames', '40',
                                     '--travel-script', '5:move:3 20:move:2')
        self.assertIn('travel: world 0 -> 3', result.stderr)
        self.assertEqual(summary['world'], 0)
        self.assertEqual(m['travels'], 2)
        self.assertTrue(133 <= m['tile'][0] <= 151 and 118 <= m['tile'][1] <= 135, m)   # gate 17's area


if __name__ == '__main__':
    unittest.main()
