"""INVENTORY-FX: the hero's equipment in the inventory window and the icons' effects.

Portable: reconstructed/hud's inventory item render (mu_inventory_item_pass, 0x00b913a2) places the equipment of
authored frames: empty codes are skipped, the armour slot of the short-armour classes is 0.75 high, a frame without
a CharacterMachine draws no equipment and an invisible frame nothing; mu_equip_slot_info keeps slots 0..14 only;
mu_icon_glow_of takes the level, option and ext from RenderObjectScreen's arguments.

Private (MU_RECOVERY_INTEGRATION=1): validate_inventory_fx against the pinned client with its mutants; with
MU_GAME_ROOT, MU_NATIVE_DATA_DIR (objects/, gfx/, lang/) and MU_GFX_LIB, mu-world's GFx inventory with Ironclad's
session records lists his three items in the equipment slots with their levels and options, the Cookery Short
Sword's gated pre-draw program is hidden at the icon (its screen position / 100 lies outside the world polygon),
and a Xeno Blade in the grid sends its ungated program's sprites to the world's list (none refused).
"""
import ctypes
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
ROOT = NATIVE.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_inventory_fx as vfx  # noqa: E402

GAME = os.environ.get('MU_GAME_ROOT')
DATA = os.environ.get('MU_NATIVE_DATA_DIR')
GFX = os.environ.get('MU_GFX_LIB')
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
SCENE = bool(PRIVATE and GAME and DATA and GFX and Path(GFX).is_file() and Path(DATA, 'gfx').is_dir())
IRONCLAD = ['weapon0=Item/CookriShortSword.bmd@0:68:9:1', 'weapon1=Item/Shield01.bmd@6:0:7', 'wing=Item/Wing02.bmd@12:1']


class Reconstruction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib, error = vfx.build_hud(vfx.HUD, Path(cls.tmp.name) / f'libinvfx.{vfx.SUFFIX}')
        if cls.lib is None:
            raise AssertionError(error)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_pass(self, codes, class_byte=1, visible=1, cc=0, scale=1.0):
        slots = (vfx.EquipSlot * 15)(*[vfx.EquipSlot(10.0 * s, 20.0, 40.0, 60.0) for s in range(15)])
        frame = vfx.SlotFrame(visible, 5, 600.0, 100.0, 1.0, scale, None, 0, 7)
        calls = []

        def equip(user, call):
            c = call.contents
            calls.append((c.slot, c.x, c.y, c.w, c.h, c.a20, c.frame_id))
        array = (ctypes.c_int32 * 15)(*codes) if codes is not None else None
        rc = self.lib.mu_inventory_item_pass(ctypes.byref(frame), slots, array, class_byte, cc, 1600, 1000, 0.4, 0.48,
                                             vfx.COLORFN(0), vfx.EMITFN(0), vfx.EQUIPFN(equip), None)
        return rc, calls

    def test_equipment_calls(self):
        codes = [-1] * 15
        codes[0], codes[3], codes[7] = 68, 8 * 512 + 1, 12 * 512 + 1
        rc, calls = self.run_pass(codes)
        self.assertEqual(rc, 1)
        self.assertEqual([c[0] for c in calls], [0, 3, 7])
        x, y, w, h = calls[1][1:5]
        self.assertAlmostEqual(x, (600.0 + 30.0) * 0.4, places=4)    # frame x (top left) + scale * slot x, * rate
        self.assertAlmostEqual(y, (100.0 + 20.0) * 0.48, places=4)
        self.assertAlmostEqual((w, h)[1], 0.48 * 60.0, places=4)
        self.assertEqual(calls[0][5:], (0, 7))

    def test_short_armour_classes(self):
        codes = [-1] * 15
        codes[3] = 8 * 512 + 1
        for class_byte in range(32):
            h = self.run_pass(codes, class_byte)[1][0][4]
            short = (class_byte & 15) in (2, 5, 7, 8, 9, 12, 14)
            self.assertAlmostEqual(h, 0.48 * 60.0 * (0.75 if short else 1.0), places=4, msg=class_byte)

    def test_frame_states(self):
        self.assertEqual(self.run_pass(None), (1, []))
        self.assertEqual(self.run_pass([68] * 15, visible=0), (0, []))
        self.assertEqual({c[5] for c in self.run_pass([68] * 15, cc=1)[1]}, {1})
        self.assertEqual({c[5] for c in self.run_pass([68] * 15, cc=2)[1]}, {0})

    def test_slot_info_bounds(self):
        slots = (vfx.EquipSlot * 16)()
        stored = [self.lib.mu_equip_slot_info(slots, s, 1.0, 2.0, 3.0, 4.0) for s in (-1, 0, 14, 15, 2 ** 31 - 1)]
        self.assertEqual(stored, [0, 1, 1, 0, 0])
        self.assertEqual((slots[14].x, slots[14].h, slots[15].x), (1.0, 4.0, 0.0))

    def test_icon_glow(self):
        ros = vfx.RosOut()
        ros.level_word, ros.excellent, ros.set_bits = (9 << 3) | 0x84 | 3, 1, 0x22
        g = self.lib.mu_icon_glow_of(ctypes.byref(ros))
        self.assertEqual((g.level, g.option, g.ext), (9, 1, 0x22))


@unittest.skipUnless(PRIVATE, 'original captures are opt-in (MU_RECOVERY_INTEGRATION=1)')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        """validate_inventory_fx: 0x00b913a2's equipment, 0x00b958e1, RenderPartObject's arguments and the icon
        flag against the pinned client, with mutants."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'inventory.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_inventory_fx.py'), '--mutations',
                            '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(report['families']['equip_pass']['cases'], 3000)
        self.assertEqual(report['families']['inv_flag']['cases'], 3000)
        self.assertEqual(len(report['mutants']), len(vfx.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))


def world(exe, *args):
    with tempfile.TemporaryDirectory() as tmp:
        # option.ini goes to the run's own folder, not the user's Application Support (shared by parallel modules)
        env = {**os.environ, 'MU_GFX_LIB': GFX, 'MU_LANG_DIR': str(Path(DATA, 'lang')), 'MU_GFX_SINGLE_BUFFER': '1',
               'MU_NATIVE_SETTINGS_DIR': tmp}
        result = subprocess.run([str(exe), '--game-root', GAME, '--objects-dir',
                                 str(Path(DATA, 'objects')), '--headless', '--backend', 'gl', '--no-audio',
                                 '--class', '1', '--tile', '140,130', '--gfx', str(Path(DATA, 'gfx')),
                                 '--gfx-open', 'inventory', '--frames', '30', '--every', '1000', '--out-dir', tmp,
                                 *args], capture_output=True, text=True, env=env, timeout=300)
    if result.returncode and 'headless GL' in result.stderr:
        raise unittest.SkipTest('no offscreen GL context')
    if result.returncode:
        # a signal shows as a negative code with empty stderr: name it and keep stdout's tail
        raise AssertionError(f'mu-world exit {result.returncode}\nstderr: {result.stderr[-2000:]}\n'
                             f'stdout: {result.stdout[-2000:]}')
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    gfx = next(r['gfx'] for r in rows if 'gfx' in r)
    pre = next((r for r in rows if r.get('item_pre_draw') is True), {})
    particles = next(r for r in rows if r.get('particles') is True)
    return gfx, pre, particles


@unittest.skipUnless(SCENE, 'private: MU_RECOVERY_INTEGRATION=1, MU_GAME_ROOT, MU_NATIVE_DATA_DIR, MU_GFX_LIB')
class InventoryScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE), 'world'], check=True, capture_output=True)
        # TEST-HYGIENE-001: run a private copy. Under run_test_suites.py's pool the make shim serialises builds, not
        # the runs of what they built, so another module's make may relink native/build/mu-world mid-run.
        cls.tmp = tempfile.TemporaryDirectory(prefix='inventory-scene-')
        cls.exe = Path(cls.tmp.name) / 'mu-world'
        shutil.copy2(NATIVE / 'build/mu-world', cls.exe)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_ironclad_equipment(self):
        args = [a for item in IRONCLAD for a in ('--hero-item', item)]
        gfx, pre, _ = world(self.exe, *args)
        self.assertEqual(gfx['item_models_missing'], 0)
        self.assertEqual([(e['slot'], e['code'], e['level'], e['excellent']) for e in gfx['inventory_equipment']],
                         [(0, 68, 9, 1), (1, 6 * 512, 7, 0), (7, 12 * 512 + 1, 0, 0)])
        # the sword's program is gated by TestFrustrum2D at the icon: hidden in every draw, nothing created
        inv = pre['inventory']
        self.assertEqual((inv['pre_effects'], inv['pre_refused']), (0, 0))
        self.assertGreater(inv['hidden'], 0)

    def test_without_records_no_equipment_line(self):
        gfx, pre, _ = world(self.exe)
        self.assertNotIn('inventory_equipment', gfx)
        self.assertNotIn('inventory', pre)

    def test_grid_xeno_blade_sprites_join_the_world(self):
        gfx, pre, particles = world(self.exe, '--npc-script', '1:mixadd:102:11')
        inv = pre['inventory']
        # the flag is clear at the icon too (hidden counts it), but 0x0b4c's program has no visible gate: it creates
        self.assertGreater(inv['pre_effects'], 0)
        self.assertEqual(inv['pre_refused'], 0)
        self.assertGreater(inv['hidden'], 0)
        self.assertGreaterEqual(particles['sprites_created'], inv['pre_effects'])


if __name__ == '__main__':
    unittest.main()
