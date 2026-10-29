"""Kanturu Underground/Ignis Volcano public dispatch, bounded logs and private original instructions."""
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
import validate_worlds_p2 as p2

TICK, LIGHT, REGISTER, SOUND, JOINT, PARTICLE, SPRITE = (0x12b4dd3, 0x16cacfc, 0x16d9f51, 0xa6ac96, 0x153b02c,
                                                         0x168fafd, 0x1692eb7)


class WorldsP2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = p2.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

    def create(self, world, typ, status=0):
        record = v.Record()
        record.type = typ
        record.position[:] = [100, 200, 300]
        record.scale = 2.5
        record.flag_2e = 1
        out = C.create_string_buffer(v.OBJ_SIZE)
        sector = C.c_int32()
        log = v.new_log()
        self.assertEqual(self.lib.mu_obj_create(C.byref(record), world, out, C.byref(sector), 0, C.byref(log)), status)
        return out, v.log_events(log)

    def f(self, obj, offset):
        return struct.unpack_from('<f', obj.raw, offset)[0]

    def test_public_create_tables(self):
        obj, events = self.create(137, 3)
        self.assertEqual(events, [(p2.PLAY_SPEED, 0, 3, p2.ALL, v.bits(0.3)), (REGISTER, 0, 0)])
        self.assertEqual(obj.raw[7], 0)                                   # +0x2e flag cleared
        self.assertEqual(self.f(self.create(137, 96)[0], 0xc0), -300)
        self.assertEqual(struct.unpack_from('<i', self.create(137, 122)[0].raw, 0x68)[0], -2)
        self.assertTrue(20 <= struct.unpack_from('<i', self.create(137, 126)[0].raw, 0x34)[0] < 50)
        obj, events = self.create(138, 45)
        self.assertEqual((self.f(obj, 0xc0), obj.raw[0xa], events), (-800, 1, []))
        self.assertEqual(self.create(138, 148)[1], [(p2.MODEL_STREAM, 0, 0)])
        self.assertEqual(struct.unpack_from('<i', self.create(138, 176)[0].raw, 0x68)[0], -2)
        self.assertEqual(self.f(self.create(138, 12)[0], 0xc0), -30)   # outside every table
        self.assertEqual(self.f(self.create(136, 0, status=2)[0], 0xc0), -30)   # sibling world untouched

    def move(self, world, typ, rand=0, time=0.0, action=0, frame=0.0):
        obj, _ = self.create(world, typ)
        struct.pack_into('<fff', obj, 0xd8, 1, 1, 0.5)
        struct.pack_into('<H', obj, 0x2a, action)
        struct.pack_into('<f', obj, 0xd0, frame)
        inputs = v.MoveInputs()
        inputs.world = world
        inputs.has_model = 1
        inputs.scene_state = 6
        inputs.time = time
        inputs.rand_fn = v.RAND_FN(lambda ctx: rand)
        inputs.speed = v.SPEED_FN(lambda ctx, t, a: 0)
        log = v.new_log()
        self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), 0)
        return obj, v.log_events(log)

    def test_public_move(self):
        obj, events = self.move(137, 10, time=-1047.1975)                 # sin = -1: clamped at 0.1
        self.assertEqual(([e[0] for e in events], self.f(obj, 0xa8), self.f(obj, 0xbc)), ([TICK], v.f32(0.1), v.f32(0.04)))
        obj, _ = self.move(137, 38, time=1570.7964)
        self.assertEqual(self.f(obj, 0xa8), 1.0)
        _, events = self.move(137, 125)                                   # deferred after the tick
        self.assertEqual([e[0] for e in events], [TICK, 0xe0913c])
        _, events = self.move(138, 88, rand=1)
        f = v.f32
        s = f(4 * f(0.1))
        self.assertEqual(events[1][:2], (LIGHT, 0))
        self.assertEqual(struct.unpack('<5f', struct.pack('<5I', *events[1][2:7])),
                         (100, 200, f(s * f(0.8)), f(s * f(0.3)), f(s * f(0.04))))
        self.assertEqual(self.move(138, 177, action=1, frame=7.5)[1][1], (SOUND, 0, 0x570, 1, 0))
        self.assertEqual(len(self.move(138, 177, action=3, frame=28.0)[1]), 1)

    def test_visual_requests_and_missing_bones(self):
        obj, _ = self.create(137, 8)
        rand = v.RAND_FN(lambda ctx: 0)
        log = v.new_log()
        self.assertEqual(self.lib.mu_kanturu_ug_visual(obj, 0, 1, 0.0, rand, p2.BONE(), None, C.byref(log)), 1)
        self.assertEqual(log.count, 0)                                    # no bones: nothing requested
        bone = p2.BONE(lambda ctx, k, local, out: [out.__setitem__(q, (1, 2, 3)[q]) for q in range(3)])
        self.assertEqual(self.lib.mu_kanturu_ug_visual(obj, 0, 1, 0.0, rand, bone, None, C.byref(log)), 1)
        events = v.log_events(log)
        self.assertEqual([e[0] for e in events], [PARTICLE, SPRITE, JOINT])
        self.assertEqual(events[2][2], 0x7f7c)
        self.assertEqual(struct.unpack('<6f', struct.pack('<6I', *events[2][3:9])), (-49, 2, 13, 1, 2, 13))
        obj, _ = self.create(137, 54)
        log = v.new_log()
        self.assertEqual(self.lib.mu_kanturu_ug_visual(obj, 0, 1, 0.0, rand, p2.BONE(), None, C.byref(log)), 1)
        e = v.log_events(log)[0]
        self.assertEqual((e[0], e[2], e[12], e[13], struct.unpack('<f', struct.pack('<I', e[14]))[0]),
                         (JOINT, 0x7f7d, 14, 1, 75.0))
        self.assertEqual(self.lib.mu_kanturu_ug_visual(obj, 0, 0, 0.0, rand, p2.BONE(), None, C.byref(log)), 0)
        self.assertEqual(self.lib.mu_ignis_visual(obj, 0), 0)

    def test_full_logs_do_not_change_state_or_rng(self):
        for typ in (3, 10, 54, 8, 125):
            results = []
            for capacity in (0, 1, 64):
                obj = C.create_string_buffer(v.OBJ_SIZE)
                struct.pack_into('<i', obj, 0x5c, typ)
                rng = v.MsvcRand(5)
                fn = v.RAND_FN(lambda ctx: rng())
                inputs = v.MoveInputs()
                inputs.world = 137
                inputs.rand_fn = fn
                log = v.new_log(capacity)
                bone = p2.BONE(lambda ctx, k, local, out: None)
                self.lib.mu_kanturu_ug_create(obj, 0, 137, fn, None, C.byref(log))
                for _ in range(8):
                    self.lib.mu_kanturu_ug_move(obj, 0, C.byref(inputs), p2.ACTION_FN(), 0.1, C.byref(log))
                    self.lib.mu_kanturu_ug_visual(obj, 0, 1, 0.0, fn, bone, None, C.byref(log))
                results.append((obj.raw, rng.seed))
                self.assertLessEqual(log.count, capacity)
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-p2-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_p2.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(len(result['families']), 6)
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 6000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 35)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            subprocess.run([sys.executable, str(ROOT / 'scripts/world_handler_coverage.py')], check=True)


if __name__ == '__main__':
    unittest.main()
