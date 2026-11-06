"""Aquila's Temple/Debenter/Boss Battle/world 115 public dispatch, bounded logs and private original instructions."""
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
import validate_worlds_s as ws

LIGHT, PARTICLE, SPRITE = 0x16cacfc, 0x168fafd, 0x1692eb7


def floats(*words):
    return struct.unpack('<%df' % len(words), struct.pack('<%dI' % len(words), *words))


class WorldsSTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        lib = ws.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll
        for name in ('mu_worlds_q_create', 'mu_worlds_q_move'):
            getattr(lib, name).argtypes = [C.c_void_p, C.c_int32, C.POINTER(q.Inputs), C.POINTER(v.Log)]
        lib.mu_worlds_q_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.POINTER(q.Inputs), C.POINTER(v.Log)]
        lib.mu_worlds_q_owns.argtypes = [C.c_int32]
        cls.lib = lib

    def create(self, world, typ, status=0):
        record = v.Record()
        record.type = typ
        record.position[:] = [100, 200, 300]
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

    def test_public_create(self):
        self.assertEqual([self.f(self.create(145, t)[0], 0xc0) for t in (51, 99, 120, 143, 148, 50, 147)],
                         [-150, -150, -150, -150, -150, -30, -30])
        for world in (139, 115):   # return-false slots: the generic fields only
            obj, events = self.create(world, 51)
            self.assertEqual((self.f(obj, 0xc0), events), (-30, []))
        self.assertEqual(self.lib.mu_aquila_create(None, 145), 0)
        self.assertEqual([self.lib.mu_worlds_q_owns(w) for w in (94, 95, 96)], [0, 1, 1])   # 96: Arca War (S2)

    def move(self, world, typ, rand=0, alpha=1.0, point=(0.0, 0.0)):
        obj, _ = self.create(world, typ)
        struct.pack_into('<fff', obj, 0xd8, 1, alpha, 0.5)
        struct.pack_into('<ff', obj, 0x188, *point)
        inputs = v.MoveInputs()
        inputs.world = world
        inputs.has_model = 1
        inputs.scene_state = 6
        inputs.rand_fn = v.RAND_FN(lambda ctx: rand)
        inputs.speed = v.SPEED_FN(lambda ctx, t, a: 0)
        log = v.new_log()
        self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), 0)
        return obj, v.log_events(log)

    def test_public_move(self):
        f = v.f32
        obj, events = self.move(145, 90, rand=1)
        s = f(f(f(4 * f(0.1)) * f(0.4)) + f(0.4))
        self.assertEqual(events[1][:2], (LIGHT, 0))
        self.assertEqual(floats(*events[1][2:7]) + (events[1][7],),
                         (100, 200, f(s * f(0.1)), f(s * f(0.41)), f(s * f(0.8)), 2))
        self.assertEqual(obj.raw[0xa], 0)                                   # alpha 1.0: not after the character
        _, events = self.move(145, 137, rand=1, point=(7.0, 9.0))
        s = f(f(f(f(5.0) / f(5.0)) * f(f(1.0) - f(0.6))) + f(0.6))
        self.assertEqual(floats(*events[1][2:7]) + (events[1][7],), (7, 9, f(s * f(0.1)), f(s * f(0.41)), f(s * f(0.8)), 2))
        self.assertEqual(self.move(145, 142, point=(1.0, 2.0))[1][1][7], 3)
        self.assertEqual(self.move(145, 50, alpha=0.5)[0].raw[0xa], 1)     # alpha below 0.9
        self.assertEqual(self.move(145, 152)[0].raw[0xa], 1)
        for world in (139, 115):
            self.assertEqual(len(self.move(world, 51)[1]), 1)              # the tick only

    def test_aquila_visual(self):
        obj, _ = self.create(145, 138)
        matrix = (C.c_float * 16)(*range(16))
        self.assertEqual(self.lib.mu_aquila_visual(obj, 1, matrix), 1)
        self.assertEqual((self.f(obj, 0x188), self.f(obj, 0x18c)), (12, 13))
        obj, _ = self.create(145, 141)
        self.lib.mu_aquila_visual(obj, 1, matrix)
        self.assertEqual(self.f(obj, 0x188), 0)
        obj, _ = self.create(145, 136)
        self.assertEqual(self.lib.mu_aquila_visual(obj, 1, None), 1)      # no pose: nothing written
        self.assertEqual(self.f(obj, 0x188), 0)
        self.assertEqual(self.lib.mu_aquila_visual(obj, 0, matrix), 0)
        self.assertEqual([self.lib.mu_aquila_bone_type(t) for t in (135, 136, 140, 141, 142)], [0, 1, 1, 0, 1])
        for name in ('boss_battle_create', 'boss_battle_move', 'boss_battle_visual', 'world115_create',
                     'world115_move'):
            self.assertEqual(getattr(self.lib, 'mu_' + name)(obj, 139), 0)

    def inputs(self, rand, bone=None, actions=None, time=0.0, now=0):
        keep = [v.RAND_FN(lambda ctx: rand()), q.BONE_FN(bone) if bone else q.BONE_FN(),
                q.ACTIONS_FN(actions) if actions else q.ACTIONS_FN()]
        inputs = q.Inputs(95, time, 0.1, now, (C.c_float * 3)(), (C.c_int32 * 2)(), keep[2], keep[0], keep[1],
                          None, None)
        return inputs, keep

    def test_debenter(self):
        obj = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<ii', obj, 0x5c, 9, 9)
        inputs, keep = self.inputs(lambda: 0)
        log = v.new_log()
        self.assertEqual(self.lib.mu_worlds_q_create(obj, 0, C.byref(inputs), C.byref(log)), -1)   # no pose
        self.assertEqual((log.count, self.i(obj, 0x68)), (0, 0))
        struct.pack_into('<i', obj, 0x60, 60)
        self.lib.mu_worlds_q_create(obj, 0, C.byref(inputs), C.byref(log))
        self.assertEqual(self.i(obj, 0x68), -2)
        seen = []
        inputs, keep = self.inputs(lambda: 0, bone=lambda ctx, k, local, out: seen.append(k) or
                                   [out.__setitem__(i, (k, 1, 2)[i]) for i in range(3)])
        struct.pack_into('<i', obj, 0x60, 9)
        self.lib.mu_worlds_q_create(obj, 0, C.byref(inputs), C.byref(log))
        events = v.log_events(log)
        self.assertEqual((seen, [e[0] for e in events], self.f(obj, 0x188), self.f(obj, 0x194)),
                         ([23, 22], [ws.POSE, ws.JOINT, ws.JOINT], 23, 22))
        self.assertEqual((events[1][12], events[2][12], floats(events[1][14])[0]), (0x3c, 0x3d, 40))
        # move: type 9 swings when its action ended, type 50 lights with the clock
        table = C.create_string_buffer(struct.pack('<BBBBfhBBI', 0, 0, 0, 0, 0.5, 4, 0, 0, 0) * 2, 32)

        def actions(ctx, t, out):
            out[0] = 2
            return C.addressof(table)
        inputs, keep = self.inputs(lambda: 2, actions=actions)
        obj = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', obj, 0x5c, 9)
        struct.pack_into('<f', obj, 0xd0, 3.5)
        log = v.new_log()
        self.assertEqual(self.lib.mu_worlds_q_move(obj, 0, C.byref(inputs), C.byref(log)), 1)
        self.assertEqual((self.i(obj, 0x64), struct.unpack_from('<H', obj, 0x2a)[0], self.f(obj, 0xd0)), (6, 1, 0))
        inputs, keep = self.inputs(lambda: 2)
        self.assertEqual(self.lib.mu_worlds_q_move(obj, 0, C.byref(inputs), C.byref(log)), -1)   # no record
        struct.pack_into('<i', obj, 0x5c, 50)
        inputs, keep = self.inputs(lambda: 2, time=1570.7964)
        self.lib.mu_worlds_q_move(obj, 0, C.byref(inputs), C.byref(log))
        e = v.log_events(log)[-1]
        self.assertEqual((e[0], e[7]), (LIGHT, 2))
        self.assertAlmostEqual(floats(e[4])[0], 0.7 * 0.2, places=5)      # |sin(pi/2)| * 0.4 + 0.3
        # visual: bone types refuse without bones; type 63 always emits two particles; no model: nothing
        log = v.new_log()
        self.assertEqual(self.lib.mu_worlds_q_visual(obj, 0, 1, C.byref(inputs), C.byref(log)), 1)
        struct.pack_into('<i', obj, 0x5c, 11)
        self.assertEqual(self.lib.mu_worlds_q_visual(obj, 0, 1, C.byref(inputs), C.byref(log)), -1)
        struct.pack_into('<i', obj, 0x5c, 63)
        self.assertEqual(self.lib.mu_worlds_q_visual(obj, 0, 0, C.byref(inputs), C.byref(log)), 0)
        self.lib.mu_worlds_q_visual(obj, 0, 1, C.byref(inputs), C.byref(log))
        self.assertEqual([(e[0], e[2]) for e in v.log_events(log)], [(PARTICLE, 0x8089)] * 2)
        self.assertEqual([self.lib.mu_debenter_visual_bones(t) for t in (9, 11, 21, 27, 31, 63)], [23, 27, 4, 1, 1, -1])

    def test_full_logs_do_not_change_state_or_rng(self):
        def bone(ctx, k, local, out):
            for i in range(3):
                out[i] = float(k + i)
        for world, types in ((145, (90, 136, 142, 152)), (95, (9, 11, 21, 27, 50, 56, 60, 62, 65, 67))):
            for typ in types:
                results = []
                for capacity in (0, 1, 64):
                    obj = C.create_string_buffer(v.OBJ_SIZE)
                    struct.pack_into('<ii', obj, 0x5c, typ, 9)
                    rng = v.MsvcRand(5)
                    fn = v.RAND_FN(lambda ctx: rng())
                    log = v.new_log(capacity)
                    if world == 145:
                        inputs = v.MoveInputs()
                        inputs.world = world
                        inputs.rand_fn = fn
                        matrix = (C.c_float * 16)(*range(16))
                        for _ in range(64):
                            self.lib.mu_aquila_move(obj, 0, C.byref(inputs), C.byref(log))
                            self.lib.mu_aquila_visual(obj, 1, matrix)
                    else:
                        table = C.create_string_buffer(struct.pack('<BBBBfhBBI', 0, 0, 0, 0, 0.5, 2, 0, 0, 0) * 2)

                        def actions(ctx, t, out):
                            out[0] = 2
                            return C.addressof(table)
                        inputs = q.Inputs(95, 100.0, 0.1, 7, (C.c_float * 3)(), (C.c_int32 * 2)(),
                                          q.ACTIONS_FN(actions), fn, q.BONE_FN(bone), None, None)
                        self.lib.mu_worlds_q_create(obj, 0, C.byref(inputs), C.byref(log))
                        for k in range(64):
                            struct.pack_into('<f', obj, 0xd0, float(k % 5))
                            self.lib.mu_worlds_q_move(obj, 0, C.byref(inputs), C.byref(log))
                            self.lib.mu_worlds_q_visual(obj, 0, 1, C.byref(inputs), C.byref(log))
                    results.append((obj.raw, rng.seed))
                    self.assertLessEqual(log.count, capacity)
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-s-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_s.py'), '--cases', '1000',
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
