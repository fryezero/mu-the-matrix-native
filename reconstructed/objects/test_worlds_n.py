"""Nixies Lake/Deep Dungeon public dispatch, bounded logs and private original instructions."""
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
import validate_object_render as v
import validate_worlds_n as n

TICK, LIGHT, REGISTER = 0x12b4dd3, 0x16cacfc, 0x16d9f51


class WorldsNTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = n.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

    def create(self, world, typ, status=0):
        record = v.Record()
        record.type = typ
        record.position[:] = [100, 200, 300]
        record.scale = 2.5
        out = C.create_string_buffer(v.OBJ_SIZE)
        sector = C.c_int32()
        log = v.new_log()
        self.assertEqual(self.lib.mu_obj_create(C.byref(record), world, out, C.byref(sector), 0, C.byref(log)), status)
        return out, log

    def range_of(self, obj):
        return struct.unpack_from('<f', obj.raw, 0xc0)[0]

    def test_public_create_tables(self):
        for world, far in [(116, 6), (117, 50), (118, 23), (119, 35), (120, 53)]:
            self.assertEqual(self.range_of(self.create(world, far)[0]), -400)
            self.assertEqual(self.range_of(self.create(world, 8)[0]), -30)   # outside every table
        obj, log = self.create(117, 60)
        self.assertEqual(v.log_events(log), [(REGISTER, 0, 1)])
        self.assertEqual(struct.unpack_from('<3f', obj.raw, 0x134), (40, 40, 160))
        self.assertEqual(struct.unpack_from('<i', obj.raw, 0x68)[0], -2)
        obj, _ = self.create(113, 106)
        self.assertEqual((self.range_of(obj), obj.raw[0xa]), (-400, 1))
        self.assertEqual(self.range_of(self.create(113, 6)[0]), -30)
        self.assertEqual(self.range_of(self.create(112, 0, status=2)[0]), -30)   # sibling world untouched

    def move(self, world, typ, rand=0, time=0.0, capacity=4096):
        obj, _ = self.create(world, typ)
        struct.pack_into('<fff', obj, 0xd8, 1, 1, 0.5)
        inputs = v.MoveInputs()
        inputs.world = world
        inputs.has_model = 1
        inputs.scene_state = 6
        inputs.time = time
        inputs.rand_fn = v.RAND_FN(lambda ctx: rand)
        inputs.speed = v.SPEED_FN(lambda ctx, t, a: 0)
        log = v.new_log(capacity)
        self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), 0)
        return obj, v.log_events(log)

    def test_public_move_after_one_generic_tick(self):
        obj, events = self.move(119, 64, rand=1)
        self.assertEqual([e[0] for e in events], [TICK, LIGHT])
        f, s = v.f32, v.f32(4 * v.f32(0.1))
        self.assertEqual(struct.unpack('<5f', struct.pack('<5I', *events[1][2:7])),
                         (100, 200, s, f(s * f(0.6)), f(s * f(0.2))))
        self.assertEqual(events[1][7], 3)
        obj, events = self.move(116, 23, time=12345.0)
        self.assertEqual([e[0] for e in events], [TICK])
        self.assertAlmostEqual(struct.unpack_from('<f', obj.raw, 0xb0)[0], -0.345, places=6)
        obj, _ = self.move(117, 22, time=3000.0)
        self.assertEqual(obj.raw[0xb0:0xb4], struct.pack('<f', -0.0))   # signed zero kept
        obj, events = self.move(118, 52, rand=3)
        self.assertEqual(events[1][:3], (n.KEYED, 0, 0x43a))
        self.assertEqual(events[1][-3:], (0, 0, 2))                        # key = (u16)(int)2.5
        self.assertEqual(len(self.move(118, 52, rand=4)[1]), 1)
        obj, _ = self.move(113, 77, time=4321.0)
        self.assertAlmostEqual(struct.unpack_from('<f', obj.raw, 0xb0)[0], 321 * 0.0005, places=7)

    def test_full_logs_do_not_change_state_or_rng(self):
        for world, typ in [(116, 52), (117, 62), (120, 67), (118, 59), (119, 60)]:
            results = []
            for capacity in (0, 1, 64):
                record = v.Record()
                record.type = typ
                obj = C.create_string_buffer(v.OBJ_SIZE)
                rng = v.MsvcRand(5)
                inputs = v.MoveInputs()
                inputs.world = world
                inputs.rand_fn = v.RAND_FN(lambda ctx: rng())
                log = v.new_log(capacity)
                struct.pack_into('<i', obj, 0x5c, typ)
                self.lib.mu_deep_dungeon_create(obj, 0, world, C.byref(log))
                for _ in range(8):
                    self.lib.mu_deep_dungeon_move(obj, 0, C.byref(inputs), C.byref(log))
                results.append((obj.raw, rng.seed))
                self.assertLessEqual(log.count, capacity)
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-n-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_n.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(len(result['families']), 13)
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 13000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 29)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            subprocess.run([sys.executable, str(ROOT / 'scripts/world_handler_coverage.py')], check=True)


if __name__ == '__main__':
    unittest.main()
