"""CLOAK-003: armour cloths, their passes and offline hero/player callers."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_armour_cloak as a
import validate_item_cloak as v
from native.tests.test_native_item_cloak import host, IDENTITY

class ArmourCloth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib, error = v.build(v.DIR, Path(cls.tmp.name), 'armour_test')
        if cls.lib is None: raise AssertionError(error)
        a.configure(cls.lib)
        cls.bones = (C.c_float * (60 * 12))(*(IDENTITY * 60))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def make(self, cls, armour=-1, pants=-1, level=13, wing=-1, index=-1):
        c = (v.CCloth * 3)()
        h = host(self.bones)
        i = a.CArmourIn(cls, 1, armour, pants, wing, index, level, (C.c_float * 3)(0.4, 0.6, 1))
        n = self.lib.mu_cloth_armour_create(c, C.byref(i), C.byref(h))
        return c, h, i, n

    def test_class_and_equipment_cases(self):
        for cls, armour, pants, count in ((0, 0x3760, -1, 1), (0, -1, -1, 0), (3, -1, -1, 1),
                (0x43, -1, 0x37d3, 1), (0x43, -1, -1, 0), (0x83, -1, 0x37e3, 1), (4, -1, -1, 2),
                (4, 0x3754, -1, 3), (8, -1, -1, 1), (9, -1, 0x1e54, 1), (12, -1, 0x1de6, 2),
                (12, -1, 0x1de7, 2), (15, 0x375f, -1, 1), (1, 0x3760, 0x1e54, 0)):
            with self.subTest(cls=cls, armour=armour, pants=pants):
                c, h, i, n = self.make(cls, armour, pants)
                self.assertEqual(n, count)
                self.assertTrue(all(x.owner and x.vertex_count > 0 for x in c[:n]))
        self.assertEqual(self.make(15, 0x375f, wing=0x22e6)[3], 0)
        self.assertEqual(self.make(15, 0x375f, index=0)[3], 0)

    def test_flare_and_mesh_streams(self):
        for cls, pants, bitmaps, sprites in ((4, -1, [0x7911] * 4, 30),
                                            (9, 0x1e54, [0x7932, 0x7932, 0x7932, 0x7fcf, 0x7fcf, 0x7f66, 0x7f1f], 0)):
            c, h, i, n = self.make(cls, pants=pants)
            side = v.CSide.__new__(v.CSide); side.stream = []; side._sink()
            g = v.CGlobals(); self.lib.mu_cloth_default_globals(C.byref(g)); g.time = 1234
            for cloth in c[:n]:
                self.assertEqual(self.lib.mu_cloth_render(C.byref(cloth), C.byref(h), C.byref(g), None,
                                                         C.byref(side.sink)), 1)
            self.assertEqual([x[1] for x in side.stream if x[0] == 'bind'], bitmaps)
            self.assertEqual(sum(x[0] == 'sprite' for x in side.stream), sprites)

    def test_mesh_level_and_quality_boundaries(self):
        cloths, h, i, n = self.make(9, pants=0x1e54)
        cloth = cloths[0]
        for level in (6, 7, 8, 9, 10, 11, 12, 13):
            for quality in range(6):
                cloth.mesh_level = level
                g = v.CGlobals(); self.lib.mu_cloth_default_globals(C.byref(g)); g.quality = quality
                side = v.CSide.__new__(v.CSide); side.stream = []; side._sink()
                self.lib.mu_cloth_render(C.byref(cloth), C.byref(h), C.byref(g), None, C.byref(side.sink))
                expected = [0x7932, 0x7932] + ([0x7932] if level >= 9 else [])
                for minimum, q, bitmap in ((13, 4, 0x7fcf), (11, 3, 0x7fcf), (9, 2, 0x7f66), (7, 1, 0x7f1f)):
                    if level >= minimum and quality >= q:
                        expected.append(bitmap)
                self.assertEqual([x[1] for x in side.stream if x[0] == 'bind'], expected, (level, quality))

    def test_update_release_and_restore(self):
        c, h, i, n = self.make(8)
        self.assertEqual(self.lib.mu_cloth_armour_update(c, n, C.byref(i), C.byref(h)), 1)
        self.assertEqual(c[0].owner, 0)
        i.pants_type = 0x37d8
        self.lib.mu_cloth_armour_update(c, n, C.byref(i), C.byref(h))
        self.assertEqual((c[0].owner, c[0].texture_front, c[0].sphere_count), (1, 0x7958, 2))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_SECTION3'),
                     'needs private-env.sh and MU_RECOVERY_INTEGRATION=1')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'report.json'
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_armour_cloak.py'), '--cases',
                                     str(len(a.CASES)), '--frames', '2', '--output', str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-5000:] + result.stderr[-2000:])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT'),
                     'needs private-env.sh and MU_GAME_ROOT')
class WorldScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT / 'native'), '-j4', 'build/mu-walk'], check=True, capture_output=True)

    def test_armour_hero_players_and_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            # Magic Gladiator robe on hero; two Dark Lord energy cloths, Slayer mesh, class-12 halves on players.
            players = p / 'players.txt'
            players.write_text('player Crown class=0x04 at=127,125 dir=5 armor=8:4:7 pants=9:4:7\n'
                               'player Lance class=0x09 at=129,125 dir=5 pants=9:366:13\n'
                               'player Tide class=0x0c at=128,126 dir=5 pants=9:256:9\n')
            rows, images = [], []
            for every in (1, 15):
                out = p / str(every)
                result = subprocess.run([str(ROOT / 'native/build/mu-walk'), '--game-root', os.environ['MU_GAME_ROOT'],
                        '--headless', '--backend', 'soft', '--no-audio', '--width', '320', '--height', '240',
                        '--class', '3', '--tile', '128,124', '--players', str(players), '--player-range', '20',
                        '--frames', '16', '--every', str(every), '--out-dir', str(out), '--quiet'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                rows.append(next(json.loads(x) for x in result.stdout.splitlines() if x.startswith('{"cloak"')))
                images.append((out / 'frame-0015.png').read_bytes())
            self.assertEqual(rows[0]['created'], 6)
            self.assertEqual(rows[0]['steps'], 156)  # 4 cloths * 31 calls, class-12's 2 cloths * 16 calls
            self.assertEqual(rows[0]['steps'], rows[1]['steps'])
            self.assertEqual(rows[0]['wind'], rows[1]['wind'])
            self.assertEqual(images[0], images[1])
