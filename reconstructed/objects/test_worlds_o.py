"""RENDER-WORLDS-O: public lifecycle, the tile-folder rule, bounded logging and private instruction comparisons."""
import ctypes as C
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_object_render as v  # noqa: E402
import validate_worlds_o as o  # noqa: E402
PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'
TICK, PARTICLE = 0x12b4dd3, 0x168fafd


class WorldsOTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/terrain')], check=True)
        cls.lib = o.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll
        cls.terrain = C.CDLL(str(ROOT / f'reconstructed/terrain/libterrain.{v.SUFFIX}'))
        cls.terrain.mu_terrain_tile_folder.argtypes = [C.c_int32]
        cls.terrain.mu_terrain_tile_folder.restype = C.c_int32

    def create(self, world, typ, status=0):
        record = v.Record()
        record.type = typ
        record.position[:] = [100, 200, 300]
        record.scale = 2
        out = C.create_string_buffer(v.OBJ_SIZE)
        sector = C.c_int32()
        self.assertEqual(self.lib.mu_obj_create(C.byref(record), world, out, C.byref(sector), 0,
                                                C.byref(v.new_log())), status)
        return out

    def move(self, obj, world, time=392.69908142089844, capacity=64):
        inputs = v.MoveInputs()
        inputs.world, inputs.has_model, inputs.scene_state, inputs.time = world, 1, 6, time
        inputs.rand_fn = v.RAND_FN(lambda ctx: 0)
        inputs.speed = v.SPEED_FN(lambda ctx, t, a: 0)
        log = v.new_log(capacity)
        self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log))
        return v.log_events(log)

    def test_tile_folder_rule(self):
        self.assertEqual([self.terrain.mu_terrain_tile_folder(f) for f in range(127, 134)],
                         [127, 128, 129, 129, 129, 132, 133])

    def test_public_create_and_move(self):
        for world in (128, 129, 130):
            self.assertEqual(self.create(world, 23).raw[0x0a], 1)
            self.assertEqual(struct.unpack_from('<i', self.create(world, 165).raw, 0x68)[0], -2)
            self.assertEqual(struct.unpack_from('<i', self.create(world, 173).raw, 0x68)[0], -1)
            obj = self.create(world, 40)
            events = self.move(obj, world)
            self.assertEqual(sum(e[0] == TICK for e in events), 1)
            self.assertEqual((struct.unpack_from('<i', obj.raw, 0x74)[0], struct.unpack_from('<f', obj.raw, 0xa8)[0]), (0, v.f32(0.8)))
            self.assertEqual(struct.unpack_from('<f', obj.raw, 0xbc)[0], v.f32(0.05))
            obj = self.create(world, 22)
            struct.pack_into('<f', obj, 0xb4, 5.0)
            events = self.move(obj, world)
            self.assertEqual(struct.unpack_from('<i', obj.raw, 0x68)[0], -2)
            particles = [e for e in events if e[0] == PARTICLE]
            self.assertEqual(len(particles), 1)
            self.assertEqual((particles[0][2], particles[0][-3:]), (0x7fcd, (0, v.bits(1.0), 0)))
        neighbour = self.create(131, 23, status=2)   # another class, still unsupported natively
        self.assertEqual(neighbour.raw[0x0a], 0)

    def test_log_capacity_preserves_state(self):
        for world in (128, 129, 130):
            results = []
            for capacity in (0, 1, 64):
                obj = self.create(world, 22)
                struct.pack_into('<f', obj, 0xb4, 7.0)
                self.move(obj, world, capacity=capacity)
                results.append(obj.raw)
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-o-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_o.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 9000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 24)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))

    @unittest.skipUnless(PRIVATE, 'private instruction captures required')
    def test_original_tile_folder(self):
        with tempfile.TemporaryDirectory(prefix='worlds-o-tiles-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_world_tile_folder.py'), '--output',
                            str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            family = result['families']['folders']
            self.assertEqual((family['cases'], family['equal'], family['stopped']), (5700, 5700, 0))
            self.assertEqual(result['remapped_folders'], {'130': 129, '131': 129})
            self.assertGreater(result['old_rule_mismatches'], 0)
