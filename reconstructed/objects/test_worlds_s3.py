"""Imperial Guardian/Event square/Test Area public dispatch, bounded logs and private original instructions."""
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
import validate_worlds_q as q
import validate_worlds_s3 as ws

TICK, PARTICLE, SPRITE, JOINT, CREATE_EFFECT, R2_EFFECT = (0x12b4dd3, 0x168fafd, 0x1692eb7, 0x153b02c, 0x13c0eaa,
                                                           0xe68c23)


def floats(*words):
    return struct.unpack('<%df' % len(words), struct.pack('<%dI' % len(words), *words))


class WorldsS3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = ws.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

    def create(self, world, typ, status=0):
        record = v.Record()
        record.type = typ
        record.position[:] = [100, 200, 300]
        record.angle[:] = [10, 20, 725]
        record.scale = 2.5
        record.flag_2c = record.flag_2d = record.flag_2e = 1
        out = C.create_string_buffer(v.OBJ_SIZE)
        sector = C.c_int32()
        log = v.new_log()
        self.assertEqual(self.lib.mu_obj_create(C.byref(record), world, out, C.byref(sector), 0, C.byref(log)), status)
        return out, v.log_events(log)

    def f(self, obj, offset):
        return struct.unpack_from('<f', obj.raw, offset)[0]

    def i(self, obj, offset):
        return struct.unpack_from('<i', obj.raw, offset)[0]

    def move(self, world, typ, status=0, time=0.0):
        obj, _ = self.create(world, typ, 2 if 69 <= world <= 72 else 0)
        struct.pack_into('<fff', obj, 0xd8, 1, 1.0, 0.5)
        inputs = v.MoveInputs()
        inputs.world, inputs.has_model, inputs.scene_state, inputs.time = world, 1, 6, time
        inputs.rand_fn = v.RAND_FN(lambda ctx: 0)
        inputs.speed = v.SPEED_FN(lambda ctx, t, a: 0)
        log = v.new_log()
        self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), status)
        return obj, v.log_events(log)

    def test_public_create_and_move(self):
        obj, events = self.create(114, 67)                       # Loren Market's create
        self.assertEqual((self.i(obj, 0x68), events[0][0]), (-2, 0x16d9f51))
        self.assertEqual(self.create(114, 68)[0].raw[0xa], 1)
        obj, events = self.create(121, 0x1ab)
        self.assertEqual([(e[0], e[2]) for e in events], [(CREATE_EFFECT, t) for t in (0x1ab, 0x1ac, 0x1ad)])
        self.assertEqual([floats(*e[3:6]) for e in events], [(100, 160, 820), (100, 164, 820), (100, 180, 820)])
        self.assertEqual(self.create(121, 0x1a8)[1], [])
        for world in (69, 70, 71, 72):   # the host's class pass creates and moves these (rand, the class static)
            self.create(world, 0x81, status=2)
            self.move(world, 20, status=2)
        obj, events = self.move(114, 8)
        self.assertEqual((self.f(obj, 0xbc), [e[0] for e in events]), (v.f32(0.2), [TICK]))
        obj, _ = self.move(121, 22, time=1570.7964)
        self.assertAlmostEqual(self.f(obj, 0xa8), 2.0, places=5)
        self.assertEqual(self.i(self.move(121, 80)[0], 0x68), -2)

    def guardian(self, cls, typ, world=None, frame=0.0, lock=0.0, alpha=1.0, model=1):
        obj = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', obj, 0x5c, typ)
        struct.pack_into('<fff', obj, 0xd8, alpha, alpha, 0.5)   # target, alpha, rate
        struct.pack_into('<ff', obj, 0xd0, frame, 0)
        struct.pack_into('<f', obj, 0xbc, 0.25)
        clock = C.c_float(lock)
        log = v.new_log()
        al = self.lib.mu_imperial_move(obj, 0, cls, cls if world is None else world, model, C.byref(clock),
                                       C.byref(log))
        return al, obj, v.log_events(log), clock.value

    def test_guardian_create_and_move(self):
        obj = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', obj, 0x5c, 0x82)
        struct.pack_into('<fff', obj, 0x158, 1, 2, 3)
        struct.pack_into('<fff', obj, 0x164, 4, 5, -725.5)
        self.assertEqual(self.lib.mu_imperial_create(obj, 69, v.RAND_FN(lambda ctx: 0), None), 1)
        self.assertEqual((self.f(obj, 0x16c), obj.raw[0x170:0x17c], obj.raw[0x17c:0x188]),
                         (-5.0, obj.raw[0x164:0x170], obj.raw[0x158:0x164]))
        struct.pack_into('<i', obj, 0x5c, 10)
        self.assertEqual(self.lib.mu_imperial_create(obj, 71, v.RAND_FN(lambda ctx: 77), None), 0)
        self.assertEqual(self.lib.mu_imperial_create(obj, 72, v.RAND_FN(lambda ctx: 77), None), 1)
        self.assertEqual(self.i(obj, 0x60), 27)
        # move: the tick carries the type's speed; type 20 follows the class static
        self.assertEqual(self.guardian(69, 20)[2], [(TICK, 0, v.bits(0.5))])
        self.assertEqual(self.guardian(70, 123)[2], [(TICK, 0, v.bits(0.75))])
        self.assertEqual(self.guardian(71, 128)[2], [(TICK, 0, v.bits(1.5))])
        self.assertEqual(self.f(self.guardian(69, 20, frame=3.0, lock=5.0)[1], 0xd0), 5.0)     # takes the lock
        self.assertEqual(self.guardian(69, 20, frame=6.0, lock=5.0)[3], 6.0)                   # leads
        self.assertEqual(self.guardian(69, 20, frame=3.0, lock=13.5)[3], 3.0)                  # lock too far ahead
        self.assertEqual(self.f(self.guardian(71, 64)[1], 0xbc), v.f32(0.44))
        self.assertEqual(self.f(self.guardian(72, 64)[1], 0xbc), v.f32(0.64))
        al, obj, _, _ = self.guardian(70, 0x52)
        self.assertEqual((al, self.i(obj, 0x68), self.f(obj, 0xb0)), (1, -2, v.f32(0.015)))   # 70: no break
        al, obj, _, _ = self.guardian(69, 0x52)
        self.assertEqual((al, self.i(obj, 0x68), self.f(obj, 0xb0)), (1, -2, 0.0))
        self.assertEqual(self.guardian(72, 20, world=74)[0], 1)                                # 72's predicate: 72..74
        self.assertEqual(self.guardian(69, 20, world=70)[0:3:2], (0, []))
        self.assertEqual(self.guardian(69, 20, alpha=0.0)[0:3:2], (0, []))
        self.assertEqual(self.guardian(69, 20, model=0)[0:3:2], (0, []))

    def visual(self, cls, typ, bones=True, rand=0, time=0.0, frame=0.0, world=None):
        obj = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', obj, 0x5c, typ)
        struct.pack_into('<f', obj, 0xa0, 2.0)
        struct.pack_into('<f', obj, 0xd0, frame)
        seen = []

        def bone(ctx, k, local, out):
            seen.append(k)
            for n in range(3):
                out[n] = float(k + n)
        keep = [v.RAND_FN(lambda ctx: rand), q.BONE_FN(bone) if bones else q.BONE_FN()]
        inputs = q.Inputs(cls if world is None else world, time, 0.1, 0, (C.c_float * 3)(), (C.c_int32 * 2)(),
                          q.ACTIONS_FN(), keep[0], keep[1], None, None)
        log = v.new_log()
        al = self.lib.mu_imperial_visual(obj, 0, cls, C.byref(inputs), C.byref(log))
        return al, [(e[0], e[2]) for e in v.log_events(log)], seen

    def test_guardian_visual(self):
        self.assertEqual(self.visual(69, 12), (1, [(SPRITE, 0x7f6b)] * 4, [2, 3]))
        self.assertEqual(self.visual(69, 12, bones=False)[:2], (-1, []))
        self.assertEqual(self.visual(69, 20, frame=6.0, rand=1)[1], [(JOINT, 0x7fd5)] * 4 + [(PARTICLE, 0x7f25)])
        self.assertEqual(self.visual(69, 51, frame=16.0)[:2], (1, []))
        self.assertEqual(self.visual(72, 51, frame=6.0)[:2], (0, []))                 # class 72 has no case 51
        self.assertEqual(self.visual(69, 64, frame=10.0)[1], [(PARTICLE, 0x7f89)] * 3)
        self.assertEqual(len(self.visual(69, 85, rand=3)[1]), 7)                      # rand % 4 + 4 effects
        self.assertEqual(self.visual(69, 85, time=2.0)[1], [])
        self.assertEqual(self.visual(72, 157)[2], [22, 23, 25, 26, 24, 21])
        self.assertEqual(len(self.visual(72, 157)[1]), 42)
        self.assertEqual(self.visual(72, 157, world=73)[:2], (1, []))
        self.assertEqual(self.visual(69, 157)[:2], (0, []))
        self.assertEqual(self.visual(70, 132)[1], [(PARTICLE, 0x7f5a)] * 3)
        self.assertEqual(self.visual(70, 132, world=71)[:2], (0, []))
        self.assertEqual([self.lib.mu_imperial_visual_bones(c, t) for c, t in ((69, 12), (69, 37), (69, 50),
                                                                               (69, 157), (72, 157), (72, 20))],
                         [3, 1, 7, -1, 26, -1])

    def test_event_square_and_test_area_visuals(self):
        obj, _ = self.create(114, 57)
        log = v.new_log()
        fn = v.RAND_FN(lambda ctx: 1)
        bone = self.lib.mu_event_square_visual.argtypes[5]()
        self.assertEqual(self.lib.mu_event_square_visual(obj, 0, 114, 0.0, fn, bone, None, C.byref(log)), 1)
        self.assertEqual([(e[0], e[2]) for e in v.log_events(log)], [(SPRITE, 0x7ef7), (PARTICLE, 0x806e)])
        self.assertEqual(self.lib.mu_event_square_visual(obj, 0, 79, 0.0, fn, bone, None, C.byref(log)), 0)
        obj, _ = self.create(121, 70)
        log = v.new_log()
        self.assertEqual(self.lib.mu_test_area_visual(obj, 0, 1, v.RAND_FN(lambda ctx: 2), None, C.byref(log)), 1)
        self.assertEqual([e[2] for e in v.log_events(log)], [0x8089, 0x8086])
        self.assertEqual(self.lib.mu_test_area_visual(obj, 0, 0, fn, None, C.byref(log)), 0)

    def test_full_logs_do_not_change_state_or_rng(self):
        def bone(ctx, k, local, out):
            for n in range(3):
                out[n] = float(k + n)
        for cls, types in ((69, (12, 20, 50, 64, 79, 85, 86, 131, 132)), (72, (10, 20, 64, 157, 158))):
            for typ in types:
                results = []
                for capacity in (0, 1, 64):
                    obj = C.create_string_buffer(v.OBJ_SIZE)
                    struct.pack_into('<i', obj, 0x5c, typ)
                    struct.pack_into('<fff', obj, 0xd8, 1, 1.0, 0.5)
                    rng = v.MsvcRand(5)
                    fn = v.RAND_FN(lambda ctx: rng())
                    log = v.new_log(capacity)
                    lock = C.c_float(0)
                    inputs = q.Inputs(cls, 100.0, 0.1, 0, (C.c_float * 3)(), (C.c_int32 * 2)(), q.ACTIONS_FN(), fn,
                                      q.BONE_FN(bone), None, None)
                    self.lib.mu_imperial_create(obj, cls, fn, None)
                    for k in range(64):
                        struct.pack_into('<f', obj, 0xd0, float(k % 30))
                        self.lib.mu_imperial_move(obj, 0, cls, cls, 1, C.byref(lock), C.byref(log))
                        self.lib.mu_imperial_visual(obj, 0, cls, C.byref(inputs), C.byref(log))
                    results.append((obj.raw, rng.seed, lock.value))
                    self.assertLessEqual(log.count, capacity)
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-s3-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_s3.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(len(result['families']), len(ws.BODIES))
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 1000 * len(ws.BODIES))
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(ws.MUTANTS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            subprocess.run([sys.executable, str(ROOT / 'scripts/world_handler_coverage.py')], check=True)


if __name__ == '__main__':
    unittest.main()
