"""CLOAK-004: NPC cloth selection, original instructions and the offline actor callers."""
import ctypes as C
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_npc_cloak as n
import validate_armour_cloak as a
import validate_item_cloak as v
from native.tests.test_native_item_cloak import host, IDENTITY

class NpcCloth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib, error = v.build(v.DIR, Path(cls.tmp.name), 'npc_test')
        if cls.lib is None: raise AssertionError(error)
        n.configure(a.configure(cls.lib))
        cls.bones = (C.c_float * (60 * 12))(*(IDENTITY * 60))

    @classmethod
    def tearDownClass(cls): cls.tmp.cleanup()

    def test_all_class_indices_and_neighbours(self):
        for index in n.INDICES:
            with self.subTest(index=index):
                cloths = (v.CCloth * 3)(); h = host(self.bones)
                count = self.lib.mu_cloth_npc_create(cloths, index, C.byref(h))
                expected = 1 if index in (55, 361) else 2 if index in (937, 939, 940, 941) else 0
                self.assertEqual(count, expected)
                self.assertTrue(all(c.owner and c.vertex_count for c in cloths[:count]))
                if index in (937, 939, 940, 941):
                    self.assertEqual([c.texture_front for c in cloths[:count]], [0x84e6, 0x84e7])
                    self.assertEqual([c.uv_offset[0] for c in cloths[:count]], [0, 1])
                    self.assertEqual([c.spheres[0].offset[0] for c in cloths[:count]], [-10, 10])

    def test_world_specific_nightmare_model(self):
        scale = C.c_float(7)
        self.assertEqual(self.lib.mu_cloth_npc_model(361, 0, C.byref(scale)), -1)
        self.assertEqual(scale.value, 7)
        self.assertEqual(self.lib.mu_cloth_npc_model(361, 39, C.byref(scale)), 0x81e)
        self.assertEqual(v.f2u(scale.value), v.f2u(1.6))
        self.assertEqual(self.lib.mu_cloth_npc_model(937, 0, C.byref(scale)), 0x95a)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_SECTION3'),
                     'needs private-env.sh')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_npc_cloak.py'), '--cases',
                '30', '--frames', '2', '--output', str(Path(tmp) / 'report.json')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout[-5000:] + result.stderr[-2000:])


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1' and os.environ.get('MU_GAME_ROOT'),
                     'needs private-env.sh')
class WorldScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(ROOT / 'native'), '-j4', 'build/mu-walk'], check=True, capture_output=True)
        cls.binary_dir = tempfile.TemporaryDirectory()
        cls.binary = Path(cls.binary_dir.name) / 'mu-walk'
        shutil.copy2(ROOT / 'native/build/mu-walk', cls.binary)

    @classmethod
    def tearDownClass(cls): cls.binary_dir.cleanup()

    def test_actor_cloths_and_saved_frame_cadence(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); placement = p / 'actors.txt'
            placement.write_text('actor 55 127 125 5 label Cloakguard\n'
                                 'actor 939 130 125 5 label EuniceDemo\n'
                                 'actor 940 132 125 5 label CapeDemo\n'
                                 'actor 941 134 125 5 label RobeDemo\n'
                                 'actor 937 128 127 5 label ClothDemo\n'
                                 'actor 361 131 127 5 label DreamDemo\n'
                                 'actor 251 126 127 5 label SmithDemo\n')
            rows, images = [], []
            for every in (1, 15):
                out = p / str(every)
                result = subprocess.run([str(self.binary), '--game-root', os.environ['MU_GAME_ROOT'],
                    '--headless', '--backend', 'soft', '--no-audio', '--width', '320', '--height', '240',
                    '--class', '1', '--hero-name', 'DemoKnight', '--tile', '128,124', '--placement', str(placement),
                    '--frames', '16', '--every', str(every), '--out-dir', str(out), '--quiet'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                rows.append(next(json.loads(x) for x in result.stdout.splitlines() if x.startswith('{"cloak"')))
                images.append((out / 'frame-0015.png').read_bytes())
                actors = [json.loads(x) for x in result.stdout.splitlines() if x.startswith('{"actor"')]
                self.assertEqual({x['class'] for x in actors}, {55, 361, 937, 939, 940, 941, 251})
                self.assertEqual(next(x for x in actors if x['class'] == 55)['player_model'], 1)
                self.assertEqual(next(x for x in actors if x['class'] == 937)['model'], 0x95a)
            self.assertEqual(rows[0]['created'], 10)
            self.assertEqual(rows[0]['drawn'], 160)
            self.assertEqual(rows[1]['drawn'], 20)
            self.assertEqual(rows[0]['steps'], rows[1]['steps'])
            self.assertEqual(images[0], images[1])

    def test_nightmare_world39_and_town_npcs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for world in (0, 2, 3, 39):
                placement = p / 'actor.txt'
                index = 361 if world == 39 else 251
                placement.write_text(f'actor {index} 129 125 5 label DemoActor\n')
                result = subprocess.run([str(self.binary), '--game-root', os.environ['MU_GAME_ROOT'],
                    '--headless', '--backend', 'soft', '--no-audio', '--width', '320', '--height', '240',
                    '--class', '1', '--hero-name', 'DemoKnight', '--world', str(world), '--tile', '128,124',
                    '--placement', str(placement), '--frames', '2', '--every', '1', '--out-dir', str(p / str(world)),
                    '--quiet'], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                actors = [json.loads(x) for x in result.stdout.splitlines() if x.startswith('{"actor"')]
                self.assertEqual(len(actors), 1)
                if world == 39:
                    self.assertEqual(actors[0]['model'], 0x81e)
                    self.assertAlmostEqual(actors[0]['scale'], 1.6)
                    row = next(json.loads(x) for x in result.stdout.splitlines() if x.startswith('{"cloak"'))
                    self.assertEqual(row['created'], 1)
                else:
                    self.assertNotIn('{"cloak"', result.stdout)

    def test_travel_recreates_actor_cloths(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); placement = p / 'actor.txt'
            placement.write_text('actor 939 129 125 5 label EuniceDemo\n')
            result = subprocess.run([str(self.binary), '--game-root', os.environ['MU_GAME_ROOT'],
                '--headless', '--backend', 'soft', '--no-audio', '--width', '320', '--height', '240',
                '--class', '1', '--hero-name', 'DemoKnight', '--tile', '128,124', '--placement', str(placement),
                '--travel-script', '5:to:2:128:124', '--frames', '10', '--every', '1', '--out-dir', str(p / 'out'),
                '--quiet'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            row = next(json.loads(x) for x in result.stdout.splitlines() if x.startswith('{"cloak"'))
            self.assertEqual(row['created'], 4)
