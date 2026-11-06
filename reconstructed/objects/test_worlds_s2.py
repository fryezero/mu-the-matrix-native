"""Nars and Arca War public dispatch, forwarding, bounded logs and private original instructions."""
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
import validate_worlds_s2 as ws

LIGHT, PARTICLE, SPRITE, EFFECT, R2_EFFECT, POSE = 0x16cacfc, 0x168fafd, 0x1692eb7, 0x13c0eaa, 0xe68c23, 0xe264a1


class Handler(C.Structure):   # mu_q_handler with RENDER-WORLDS-S2's Arca War stage
    _fields_ = q.Handler._fields_ + [('arca_stage', C.c_int32)]


def floats(*words):
    return struct.unpack('<%df' % len(words), struct.pack('<%dI' % len(words), *words))


class WorldsS2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        lib = ws.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll
        for name in ('mu_worlds_q_create', 'mu_worlds_q_move'):
            getattr(lib, name).argtypes = [C.c_void_p, C.c_int32, C.POINTER(q.Inputs), C.POINTER(v.Log)]
        lib.mu_worlds_q_visual.argtypes = [C.c_void_p, C.c_int32, C.c_int, C.POINTER(q.Inputs), C.POINTER(v.Log)]
        lib.mu_worlds_q_visual_bones.argtypes = [C.c_int32, C.c_int32]
        lib.mu_worlds_q_owns.argtypes = [C.c_int32]
        cls.lib = lib

    def inputs(self, world, rand=lambda: 0, bone=True, stage=0, time=0.0, actions=None):
        handler = Handler(0, None, 1, None, stage)

        def bone_cb(ctx, k, local, out):
            for i in range(3):
                out[i] = float(k * 10 + i) + local[i]

        def actions_cb(ctx, t, out):
            out[0] = len(actions.raw) // 16
            return C.addressof(actions)
        keep = [handler, v.RAND_FN(lambda ctx: rand()), q.BONE_FN(bone_cb) if bone else q.BONE_FN(),
                q.ACTIONS_FN(actions_cb) if actions is not None else q.ACTIONS_FN()]
        return q.Inputs(world, time, 0.1, 0, (C.c_float * 3)(), (C.c_int32 * 2)(), keep[3], keep[1], keep[2], None,
                        C.cast(C.pointer(handler), C.POINTER(q.Handler))), keep

    def obj(self, typ, **fields):
        o = C.create_string_buffer(v.OBJ_SIZE)
        struct.pack_into('<i', o, 0x5c, typ)
        struct.pack_into('<ii', o, 0x68, -1, -1)
        struct.pack_into('<f', o, 0xc0, -30.0)
        struct.pack_into('<3f', o, 0x158, 1000.0, 2000.0, 0.0)
        struct.pack_into('<f', o, 0xa0, 2.5)
        for offset, fmt, value in fields.values():
            struct.pack_into(fmt, o, offset, value)
        return o

    def f(self, o, offset, n=1):
        values = struct.unpack_from('<%df' % n, o.raw, offset)
        return values[0] if n == 1 else values

    def i(self, o, offset):
        return struct.unpack_from('<i', o.raw, offset)[0]

    def run_slot(self, slot, world, o, **kw):
        inputs, keep = self.inputs(world, **kw)
        log = v.new_log()
        if slot == 'visual':
            r = self.lib.mu_worlds_q_visual(o, 0, 1, C.byref(inputs), C.byref(log))
        else:
            r = getattr(self.lib, 'mu_worlds_q_' + slot)(o, 0, C.byref(inputs), C.byref(log))
        return r, v.log_events(log)

    def test_ownership_and_base_worlds(self):
        self.assertEqual([w for w in range(85, 135) if self.lib.mu_worlds_q_owns(w)],
                         [91, 92, 95, 96, 110, 111, 112, 122, 123, 124, 125, 126, 127])
        self.assertEqual([self.lib.mu_arca_base_world(w) for w in (91, 92, 96, 100, 101, 110, 111, 112)],
                         [-1, 91, 95, -1, 100, -1, 110, -1])
        self.assertEqual([self.lib.mu_worlds_q_visual_bones(w, t) for w, t in
                          ((110, 87), (111, 87), (111, 0x59b), (92, 0x59b), (92, 9), (96, 9), (110, 14))],
                         [15, 15, 3, 3, 17, 23, -1])

    def test_nars_create_move_visual(self):
        for world in (110, 111):   # 111 through the Arca War class
            for typ, offset, value in ((14, 0x68, -2), (11, 0xc0, -200.0), (8, 0xc0, -800.0), (19, 0xc0, -400.0),
                                       (0, 0xc0, -30000.0), (0, 0xa0, 17.0), (0, 0x16c, 340.0)):
                o = self.obj(typ)
                self.assertEqual(self.run_slot('create', world, o)[0], 1)
                self.assertEqual(self.i(o, offset) if isinstance(value, int) else self.f(o, offset), value)
            o = self.obj(6)
            self.run_slot('create', world, o)
            self.assertEqual((self.f(o, 0xc0), o.raw[0xa]), (-200.0, 1))
            o = self.obj(85)
            self.run_slot('create', world, o, rand=lambda: 7)
            self.assertEqual(self.i(o, 0x64), 2100)
        o = self.obj(134)
        self.assertEqual(self.run_slot('create', 110, o, bone=False)[0], -1)   # needs the model posed
        r, events = self.run_slot('create', 110, o)
        self.assertEqual((r, events[0][0], floats(*events[0][2:6])), (1, POSE, (1000.0, 2000.0, 0.0, 2.5)))
        self.assertEqual(self.f(o, 0x110, 3), (40.0, 41.0, 42.0))
        o = self.obj(14)
        self.run_slot('create', 112, o)   # Ferea's class, not Nars: no HiddenMesh
        self.assertEqual(self.i(o, 0x68), -1)
        # move: flame lights of 4/116/146 (range 1, own x/y) and 134 (range 2, +0x110); 77 scrolls
        r, events = self.run_slot('move', 110, self.obj(4), rand=lambda: 3)
        self.assertEqual((events[0][0], floats(*events[0][2:4]), events[0][7]), (LIGHT, (1000.0, 2000.0), 1))
        self.assertAlmostEqual(floats(events[0][4])[0], 0.92, places=5)
        o = self.obj(134)
        struct.pack_into('<3f', o, 0x110, 5.0, 6.0, 7.0)
        r, events = self.run_slot('move', 111, o)
        self.assertEqual((floats(*events[0][2:4]), events[0][7]), ((5.0, 6.0), 2))
        o = self.obj(77)
        self.run_slot('move', 110, o)
        self.assertAlmostEqual(self.f(o, 0xb0), -0.015, places=6)
        # visual: bone types refuse without bones; the fire family logs an unowned keyed effect and a flame
        self.assertEqual(self.run_slot('visual', 110, self.obj(87), bone=False)[0], -1)
        r, events = self.run_slot('visual', 110, self.obj(4), rand=lambda: 2)
        self.assertEqual([(e[0], e[2]) for e in events], [(R2_EFFECT, 0x413), (SPRITE, 0x7ef7)])
        self.assertEqual(floats(*events[0][3:6]), (70.0, 71.0, 72.0))   # bone 7
        self.assertEqual(events[0][-3:], (10, 0, 1))   # sub 10, owner 0, word4 = (int)(2.5 * 0.4 * 15 * 0.1)
        r, events = self.run_slot('visual', 110, self.obj(87))
        self.assertEqual([e[2] for e in events], [0x7f26] * 12)
        o = self.obj(26)
        r, events = self.run_slot('visual', 110, o)   # rand 0: 1 in 5 opens
        self.assertEqual((events[0][2], self.f(o, 0xec, 3)), (0x8184, (1.0, 0.5, v.f32(0.1))))
        self.assertEqual(self.run_slot('visual', 0, self.obj(4))[0], -1)   # not a Q world

    def test_arca_own_types_and_forwarding(self):
        for world in (92, 96, 111):
            for typ in (0x59b, 0x88a, 0x88e):
                o = self.obj(typ)
                self.assertEqual(self.run_slot('create', world, o)[0], 1)
                self.assertAlmostEqual(self.f(o, 0xa0), 0.85, places=6)
            o = self.obj(0x88f)   # not the class's: forwarded, the base class keeps the scale
            self.run_slot('create', world, o)
            self.assertEqual(self.f(o, 0xa0), 2.5)
        o = self.obj(27)   # Acheron's create through world 92
        self.run_slot('create', 92, o)
        self.assertEqual(self.f(o, 0xc0), -3000.0)
        o = self.obj(0, key=(0x60, '<i', 56))   # Debenter's create through world 96 (key +0x60)
        self.run_slot('create', 96, o)
        self.assertEqual(self.i(o, 0x68), -2)
        r, events = self.run_slot('move', 96, self.obj(50), time=1570.7964)   # Debenter's type-50 light
        self.assertEqual((events[0][0], events[0][7]), (LIGHT, 2))
        # 0x59b: CreateEffect 0x413 at bone 3 with the stage's light; subtype 10 below stage 4, else 11
        for stage, sub, light in ((0, 10, (1.0, 0.37, 0.66)), (3, 10, (0.08, 1.0, 0.86)), (4, 11, (0.6, 0.9, 0.95))):
            r, events = self.run_slot('visual', 111, self.obj(0x59b), stage=stage)
            e = events[0]
            self.assertEqual((r, e[0], e[2], floats(*e[3:6]), e[12], e[13]), (1, EFFECT, 0x413, (30.0, 31.0, 32.0),
                                                                                sub, 0))
            self.assertEqual(floats(*e[9:12]), tuple(struct.unpack('<3f', struct.pack('<3f', *light))))
            self.assertEqual(floats(e[14])[0], 2.5)
        self.assertEqual(self.run_slot('visual', 92, self.obj(0x59b), bone=False)[0], -1)
        self.assertEqual(self.run_slot('visual', 92, self.obj(0x59b), stage=6)[0], -1)   # outside the table
        self.assertEqual(self.run_slot('visual', 96, self.obj(0x88b)), (1, []))
        # world 101 on Uruk Mountain's class (object_render): create 20 range -400, own types 0.85, move 27's light
        for typ, offset, value in ((20, 0xc0, -400.0), (0x59b, 0xa0, 0.85), (0x88c, 0xa0, 0.85)):
            record = v.Record()
            record.type = typ
            record.scale = 2.5
            out = C.create_string_buffer(v.OBJ_SIZE)
            sector, log = C.c_int32(), v.new_log()
            self.assertEqual(self.lib.mu_obj_create(C.byref(record), 101, out, C.byref(sector), 0, C.byref(log)), 0)
            self.assertAlmostEqual(self.f(out, offset), value, places=6)

    def test_full_logs_do_not_change_state_or_rng(self):
        for world, types in ((110, (1, 4, 11, 14, 25, 26, 32, 85, 87, 116, 134, 146)), (111, (4, 87, 0x59b))):
            for typ in types:
                results = []
                for capacity in (0, 1, 64):
                    obj = self.obj(typ)
                    rng = v.MsvcRand(5)
                    log = v.new_log(capacity)
                    table = C.create_string_buffer(struct.pack('<BBBBfhBBI', 0, 0, 0, 0, 0.5, 2, 0, 0, 0) * 2)
                    inputs, keep = self.inputs(world, rand=rng, actions=table, stage=4)
                    self.lib.mu_worlds_q_create(obj, 0, C.byref(inputs), C.byref(log))
                    for k in range(64):
                        inputs.time = 37.0 * k
                        struct.pack_into('<f', obj, 0xd0, float(k % 5))
                        self.lib.mu_worlds_q_move(obj, 0, C.byref(inputs), C.byref(log))
                        self.lib.mu_worlds_q_visual(obj, 0, 1, C.byref(inputs), C.byref(log))
                    results.append((obj.raw, rng.seed))
                    self.assertLessEqual(log.count, capacity)
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-s2-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_s2.py'), '--cases', '1000',
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
