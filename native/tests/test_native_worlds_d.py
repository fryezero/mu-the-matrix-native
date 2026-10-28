"""Synthetic world-to-effect integration for RENDER-WORLDS-D, no captured data."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import native_fixtures as nf
from test_native_world import write_open_world
from test_native_terrain import write_world
from test_native_objects import obj_plain

NATIVE = Path(__file__).resolve().parents[1]


class WarpSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-C', str(NATIVE)], check=True, capture_output=True)

    def test_world_created_portals_reach_effect_pool_and_model_renderer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = write_open_world(Path(tmp)/'game')
            npc = root/'Data/Npc'
            npc.mkdir()
            plain = Path(tmp)/'plain'
            plain.mkdir()
            for seed, name in enumerate(('warp01', 'warp02', 'warp03', 'obj_donkey', 'obj_flag'), 1):
                nf.write_textured_model(npc, seed).rename(npc/f'{name}.bmd')
            for world, tile, effects in ((2, '53,92', 3), (3, '223,30', 5), (57, '171,24', 3), (58, '169,24', 6)):
                with self.subTest(world=world):
                    folder = world+1
                    write_world(root, folder)
                    (plain/f'EncTerrain{folder}.plain').write_bytes(obj_plain(folder, []))
                    cmd = [str(NATIVE/'build/mu-walk'), '--game-root', str(root), '--world', str(world),
                           '--tile', tile, '--objects-dir', str(plain), '--headless', '--backend', 'soft', '--frames', '5', '--every', '4',
                           '--width', '1280', '--height', '768', '--no-audio', '--no-env', '--no-items',
                           '--no-names', '--no-map', '--quiet', '--out-dir', str(Path(tmp)/str(world))]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
                    report = next(r for r in rows if r.get('joints') is True)
                    self.assertEqual(report['effects_created'], effects)
                    self.assertEqual(report['effects_unsupported'], 0)
                    self.assertEqual(report['effects_live'], effects)
                    self.assertGreater(report['effect_models'], 0)
                    again = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    self.assertEqual(result.stdout, again.stdout)
