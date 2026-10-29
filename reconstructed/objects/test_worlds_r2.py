"""Twisted Karutan/Kardamahal/Swamp of Destruction public dispatch, bounded logs and private original instructions."""
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
import validate_worlds_r2 as r2

TICK, LIGHT, SOUND, JOINT, PARTICLE, SPRITE = 0x12b4dd3, 0x16cacfc, 0xa6ac96, 0x153b02c, 0x168fafd, 0x1692eb7


def floats(*words):
    return struct.unpack('<%df' % len(words), struct.pack('<%dI' % len(words), *words))


class WorldsR2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = r2.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

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

    def test_public_create_tables(self):
        self.assertEqual([self.create(142, t)[0].raw[0xa] for t in (1, 66, 120, 163, 166, 178, 198, 199)],
                         [1, 1, 1, 1, 0, 1, 1, 0])
        obj, events = self.create(143, 0)
        self.assertEqual((self.f(obj, 0x160), obj.raw[0xa], obj.raw[5], obj.raw[6], events), (64, 1, 0, 0, []))
        self.assertEqual(self.create(143, 40)[0].raw[7], 0)
        self.assertEqual((self.f(self.create(143, 168)[0], 0xc0), self.i(self.create(143, 168)[0], 0x68)), (-50, -2))
        self.assertEqual(self.i(self.create(143, 170)[0], 0x68), -1)
        self.assertEqual([self.f(self.create(143, t)[0], 0xc0) for t in (110, 115, 124)], [-230, -150, -100])
        obj = self.create(144, 64)[0]
        self.assertEqual((obj.raw[0xa], self.f(obj, 0xc0)), (1, -300))
        self.assertEqual([self.f(self.create(144, t)[0], 0xc0) for t in (127, 128, 145, 200, 201)],
                         [-300, -30, -300, -300, -30])
        self.assertEqual(self.f(self.create(145, 6, status=2)[0], 0xc0), -30)   # sibling world untouched

    def move(self, world, typ, rand=0, action=0):
        obj, _ = self.create(world, typ)
        struct.pack_into('<fff', obj, 0xd8, 1, 1, 0.5)
        struct.pack_into('<H', obj, 0x2a, action)
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
        _, events = self.move(142, 160, rand=1)
        s = f(4 * f(0.1))
        self.assertEqual(events[1][:2], (LIGHT, 0))
        self.assertEqual(floats(*events[1][2:7]) + (events[1][7],), (100, 200, s, f(s * f(0.6)), f(s * f(0.2)), 2))
        _, events = self.move(143, 113, rand=3)
        s = f(f(f(6 * f(0.1)) * f(0.4)) + f(0.4))
        self.assertEqual(floats(*events[1][4:7]) + (events[1][7],), (s, f(s * f(0.2)), f(s * f(0.1)), 3))
        _, events = self.move(143, 115)
        self.assertEqual((events[1][0], events[1][5]), (r2.BONE_LIGHTS, 4))
        obj, _ = self.create(143, 115)
        drawn = []
        inputs = v.MoveInputs()
        inputs.world = 143
        inputs.rand_fn = v.RAND_FN(lambda ctx: drawn.append(1) or 0)
        log = v.new_log()
        self.assertEqual(self.lib.mu_kardamahal_move(obj, 0, C.byref(inputs), C.byref(log)), 1)
        self.assertEqual((log.count, drawn), (0, []))                     # no model: no rand, no lights
        self.assertEqual(self.move(143, 146, action=2)[1][1], (SOUND, 0, 0x5a9, 0, 0))
        self.assertEqual(len(self.move(143, 146, action=1)[1]), 1)
        self.assertEqual(self.move(143, 151, rand=1)[1][1][2], 0x5a8)
        _, events = self.move(144, 183, rand=0)
        self.assertEqual(events[1][7], 3)
        self.assertEqual([self.lib.mu_kardamahal_bone_name(k) for k in (0, 7, 8)], [b'E002', b'E009', None])

    def test_visual_requests_writes_and_missing_bones(self):
        rand = v.RAND_FN(lambda ctx: 0)
        obj, _ = self.create(142, 72)
        log = v.new_log()
        self.assertEqual(self.lib.mu_twisted_karutan_visual(obj, 0, 1, 0.0, rand, r2.BONE(), None, C.byref(log)), 1)
        self.assertEqual(log.count, 0)                                    # no bones: nothing requested
        seen = []
        bone = r2.BONE(lambda ctx, k, local, out: seen.append((k, local[0])) or
                       [out.__setitem__(q, (1, 2, 3)[q]) for q in range(3)])
        self.lib.mu_twisted_karutan_visual(obj, 0, 1, 3926.9908, rand, bone, None, C.byref(log))
        events = v.log_events(log)
        self.assertEqual((seen, [e[2] for e in events]), ([(11, 20.0), (7, 20.0)], [0x7ef7, 0x7f26, 0x7f26, 0x7f26]))
        self.assertAlmostEqual(floats(events[0][7])[0], 0.4 * 1.3, places=5)   # |sin(pi/2)| * 0.4 * 1.3
        obj, _ = self.create(142, 115)
        log = v.new_log()
        self.lib.mu_twisted_karutan_visual(obj, 0, 1, 0.0, rand, bone, None, C.byref(log))
        self.lib.mu_twisted_karutan_visual(obj, 0, 1, 0.0, rand, bone, None, C.byref(log))
        self.assertEqual((log.count, self.i(obj, 0x68)), (20, -2))       # twenty particles once, then hidden
        obj, _ = self.create(144, 169)
        log = v.new_log()
        self.assertEqual(self.lib.mu_swamp_visual(obj, 0, 1, rand, None, C.byref(log)), 1)
        e = v.log_events(log)[0]
        self.assertEqual((e[0], e[2], e[12], e[13], floats(e[14])[0]), (JOINT, 0x7f7d, 0x19, 1, 2.5))
        self.assertEqual(tuple(round(x, 5) for x in floats(*struct.unpack_from('<3I', obj.raw, 0xec))), (1, 0.8, 0.4))
        obj, _ = self.create(143, 161)
        log = v.new_log()
        self.lib.mu_kardamahal_visual(obj, 0, 1, v.RAND_FN(lambda ctx: 81), None, C.byref(log))
        e = v.log_events(log)[0]
        self.assertEqual((e[0], e[2], e[12], e[13], e[14]), (r2.EFFECT, 0x195, 0, 1, 2))
        self.assertEqual(self.lib.mu_kardamahal_visual(obj, 0, 0, rand, None, C.byref(log)), 0)

    def test_full_logs_do_not_change_state_or_rng(self):
        cases = [(142, (72, 113, 115, 116, 160, 196)), (143, (113, 115, 128, 150, 161)), (144, (160, 183, 185, 193))]
        for world, types in cases:
            for typ in types:
                results = []
                for capacity in (0, 1, 64):
                    obj = C.create_string_buffer(v.OBJ_SIZE)
                    struct.pack_into('<i', obj, 0x5c, typ)
                    rng = v.MsvcRand(5)
                    fn = v.RAND_FN(lambda ctx: rng())
                    inputs = v.MoveInputs()
                    inputs.world = world
                    inputs.has_model = 1
                    inputs.rand_fn = fn
                    log = v.new_log(capacity)
                    bone = r2.BONE(lambda ctx, k, local, out: None)
                    for _ in range(64):
                        if world == 142:
                            self.lib.mu_twisted_karutan_move(obj, 0, C.byref(inputs), C.byref(log))
                            self.lib.mu_twisted_karutan_visual(obj, 0, 1, 0.0, fn, bone, None, C.byref(log))
                        elif world == 143:
                            self.lib.mu_kardamahal_move(obj, 0, C.byref(inputs), C.byref(log))
                            self.lib.mu_kardamahal_visual(obj, 0, 1, fn, None, C.byref(log))
                        else:
                            self.lib.mu_swamp_move(obj, 0, C.byref(inputs), C.byref(log))
                            self.lib.mu_swamp_visual(obj, 0, 1, fn, None, C.byref(log))
                    results.append((obj.raw, rng.seed))
                    self.assertLessEqual(log.count, capacity)
                self.assertEqual(results[0], results[1])
                self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-r2-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_r2.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(len(result['families']), 9)
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 9000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(r2.MUTANTS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            subprocess.run([sys.executable, str(ROOT / 'scripts/world_handler_coverage.py')], check=True)


if __name__ == '__main__':
    unittest.main()
