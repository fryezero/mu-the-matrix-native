"""RENDER-ITEMS-CALLERS-001: RenderObjDraw's item pre-draw programs (RENDER-ITEMS-002R) from the world callers.

Portable: native/world/world_item_pre.h (the TestFrustrum2D flag at the item's OBJECT, compiled with the
reconstructed terrain test): inside the polygon in view, outside and on the -20 margin out of view.

Private, original instructions (MU_RECOVERY_INTEGRATION=1, pinned text/data): scripts/validate_item_callers.py
with its mutants (validator row validate_item_callers).

Private, installed data (MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT): Lorencia through `mu-walk` with demo players
wearing pre-draw types (sword 0x0b27, shield 0x1748, wing 0x2382, bow 0x1316, wing 0x2394, mace 0x0f1c, sword
0x0b4c, wing 0x2384) and ground drops (wing 0x2384, sword 0x0b4c, bow 0x1311):
  * the players' and ground items' requests become sprites (pre_effects > 0); since RENDER-EFFECTS-020 the wing
    0x2384's OBJECT-owned particles (0x810a/0x11, 0x81cf/0) are created with the item OBJECT as owner: nothing
    is refused;
  * a player outside the frame's polygon has the flag clear: no requests, counted as hidden;
  * the demo players file: before APP-POLISH-008 it wore no pre-draw type and printed no item_pre_draw line; its
    four new outfits (shield 0x1748, sword 0x0b4c, wings 0x230b / 0x2311, mace 0x0f1c) now create their sprites
    with none refused.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent
ROOT = NATIVE.parent
WALK = NATIVE/'build/mu-walk'
GAME = os.environ.get('MU_GAME_ROOT')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'

PLAYERS = (
    'player Blade  class=0x01 at=129,124 dir=3 pk=3 level=400 helm=7:9:7 armor=8:9:7 pants=9:9:7 gloves=10:9:7 '
    'boots=11:9:7 weapon0=0:65:9 weapon1=6:98:9 wing=12:156:0\n'
    'player Archer class=0x02 at=127,125 dir=1 pk=3 level=400 helm=7:3:5 armor=8:3:5 pants=9:3:5 gloves=10:3:5 '
    'boots=11:3:5 weapon0=4:48:7 wing=12:174:0\n'
    'player Maul   class=0x04 at=130,122 dir=5 pk=3 level=400 armor=8:4:7 pants=9:4:7 gloves=10:4:7 boots=11:4:7 '
    'helm=7:4:7 weapon0=2:54:7\n'
    'player Seraph class=0x00 at=126,122 dir=2 pk=3 level=400 helm=7:10:7 armor=8:10:7 pants=9:10:7 '
    'gloves=10:10:7 boots=11:10:7 weapon0=0:102:7 wing=12:158:0\n')
DROPS = '1:drop:6302:0:127,123 1:drop:102:0:129,123 1:drop:2091:0:128,125'


def walk(players_text, *args, frames=60):
    with tempfile.TemporaryDirectory() as tmp:
        players = Path(tmp)/'players.txt'
        players.write_text(players_text)
        result = subprocess.run([str(WALK), '--game-root', GAME, '--headless', '--backend', 'soft', '--no-audio',
                                 '--width', '320', '--height', '240', '--every', '1000', '--out-dir', tmp,
                                 '--tile', '128,124', '--players', str(players), '--player-range', '20',
                                 '--frames', str(frames), '--quiet', *args], capture_output=True, text=True)
    if result.returncode:
        raise AssertionError(f'mu-walk failed: {result.stderr[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    pre = next((r for r in rows if r.get('item_pre_draw') is True), None)
    particles = next(r for r in rows if r.get('particles') is True)
    return pre, particles


class FlagHeader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import ctypes
        cls.tmp = tempfile.TemporaryDirectory()
        shim = Path(cls.tmp.name)/'shim.c'
        shim.write_text('#include "native/world/world_item_pre.h"\n'
                        'int out_of_view(const float *x, const float *y, const float *o)\n'
                        '{ return mu_world_item_out_of_view(x, y, o); }\n')
        lib = Path(cls.tmp.name)/'libshim.so'
        subprocess.run(['clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-Wconversion', '-fPIC',
                        '-ffp-contract=off', '-shared', '-I', str(ROOT), str(shim),
                        str(ROOT/'reconstructed/terrain/terrain.c'), str(ROOT/'reconstructed/terrain/world_haze.c'),
                        str(ROOT/'reconstructed/record-math/record_math.c'), '-lm', '-o', str(lib)], check=True)
        cls.lib = ctypes.CDLL(str(lib))
        F = ctypes.c_float * 4
        cls.square = (F(10, 10, 20, 20), F(10, 20, 20, 10))   # the winding whose inside has d > 0

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def hidden(self, x, y, polygon=None):
        import ctypes
        xs, ys = polygon or self.square
        return self.lib.out_of_view(xs, ys, (ctypes.c_float * 3)(x, y, 999.0))

    def test_inside_is_in_view_outside_is_not(self):
        self.assertEqual(self.hidden(1500.0, 1500.0), 0)       # tile 15,15
        self.assertEqual(self.hidden(2500.0, 1500.0), 1)       # tile 25,15
        self.assertEqual(self.hidden(1500.0, 500.0), 1)

    def test_minus_twenty_margin(self):
        # the edge along y = 10: d = 10 * (y - 10) at x = 15, so in view only while y > 8 (and x in 8..22)
        self.assertEqual(self.hidden(1500.0, 810.0), 0)
        self.assertEqual(self.hidden(1500.0, 790.0), 1)
        self.assertEqual(self.hidden(2190.0, 1500.0), 0)
        self.assertEqual(self.hidden(2210.0, 1500.0), 1)

    def test_clockwise_polygon_hides_everything(self):
        import ctypes
        F = ctypes.c_float * 4
        self.assertEqual(self.hidden(1500.0, 1500.0, (F(10, 20, 20, 10), F(10, 10, 20, 20))), 1)


@unittest.skipUnless(PRIVATE, 'original captures are opt-in (MU_RECOVERY_INTEGRATION=1)')
class ItemCallers(unittest.TestCase):
    def test_original_instructions(self):
        """validate_item_callers: the flag chain and the caller order against the pinned client."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'callers.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_item_callers.py'), '--mutations',
                            '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(report['families']['link_flag']['cases'], 3000)
        self.assertEqual(len(report['mutants']), 6)
        self.assertTrue(all(report['mutants'].values()))


@unittest.skipUnless(PRIVATE and GAME, 'needs MU_RECOVERY_INTEGRATION=1 and MU_GAME_ROOT')
class WorldPreDraw(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'build/mu-walk'], check=True, capture_output=True)

    def test_players_and_ground_items_create_their_pre_draw_effects(self):
        pre, particles = walk(PLAYERS, '--items', '--item-script', DROPS)
        self.assertIsNotNone(pre)
        # RENDER-EFFECTS-020: 92 / 2 and 18 / 1 before (the refusals were 0x2384's OBJECT-owned particles). The first
        # created 0x810a/0x11 draws its eight rand() calls (133 -> 141), so the later gates and request counts move.
        self.assertEqual(pre['players'], {'pre_effects': 93, 'pre_refused': 0, 'hidden': 0})
        self.assertEqual(pre['ground'], {'pre_effects': 18, 'pre_refused': 0, 'hidden': 0})
        self.assertEqual(pre['hero'], {'pre_effects': 0, 'pre_refused': 0, 'hidden': 0})
        # CLOAK-003: Maul's Dark Lord energy cloth adds 6*5 flare sprites on each of the two saved draws.
        self.assertEqual(particles['sprites_created'], 110 + 2 * 6 * 5)
        self.assertEqual(particles['rand_calls'], 141)
        self.assertEqual((particles['created'], particles['unsupported']), (7, 0))

    def test_flag_clear_outside_the_polygon(self):
        pre, _ = walk('player Far class=0x01 at=138,114 dir=3 pk=3 level=400 weapon0=0:65:9 wing=12:156:0\n',
                      frames=20)
        self.assertEqual(pre['players']['pre_effects'], 0)
        self.assertGreater(pre['players']['hidden'], 0)

    def test_demo_players_draw_their_pre_draw_effects(self):
        pre, _ = walk((NATIVE/'world/lorencia-demo-players.txt').read_text(), frames=20)
        self.assertEqual((pre['players']['pre_effects'], pre['players']['pre_refused']), (98, 0))   # APP-POLISH-008
        self.assertEqual(pre['hero'], {'pre_effects': 0, 'pre_refused': 0, 'hidden': 0})


if __name__ == '__main__':
    unittest.main()
