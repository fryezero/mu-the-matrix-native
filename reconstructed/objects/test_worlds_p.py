"""RENDER-WORLDS-P public dispatch, bounded logging and private instruction comparisons."""
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
import validate_worlds_p as p
MU_WP_CREATE, MU_WP_MOVE, TICK = 0x00e3a4dc, 0x00e3a719, 0x12b4dd3


class WorldsPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = p.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

    def create(self, world, typ):
        record = v.Record()
        record.type = typ
        record.position[:] = [100, 200, 300]
        record.scale = 2
        out = C.create_string_buffer(v.OBJ_SIZE)
        sector = C.c_int32()
        log = v.new_log()
        self.assertEqual(self.lib.mu_obj_create(C.byref(record), world, out, C.byref(sector), 0, C.byref(log)), 0)
        return out, v.log_events(log)

    def test_public_create_defers_kethotum_and_runs_bloody_tarkan(self):
        for world in (0x87, 0x88):
            out, events = self.create(world, 0x16)
            self.assertEqual(events, [(MU_WP_CREATE, 0, world)])
            self.assertEqual(out.raw[0x0a], 0)   # the class create has not run yet
        out, events = self.create(0x8c, 0x51)
        self.assertEqual(events, [])
        self.assertEqual(struct.unpack_from('<i', out.raw, 0x68)[0], -2)
        out, _ = self.create(0x8c, 0x44)
        self.assertEqual(out.raw[0x0a], 1)

    def test_public_move_ticks_once_then_defers_or_lights(self):
        rnd = v.RAND_FN(lambda ctx: 0)
        speed = v.SPEED_FN(lambda ctx, t, a: 0.25)
        for world, typ in [(0x87, 0x16), (0x88, 0xb5), (0x88, 0xa5), (0x8c, 0x13), (0x8c, 0x51)]:
            obj, _ = self.create(world, typ)
            inputs = v.MoveInputs()
            inputs.world, inputs.has_model, inputs.model_has_actions, inputs.scene_state = world, 1, 1, 6
            inputs.rand_fn, inputs.speed, inputs.time = rnd, speed, 1000
            log = v.new_log()
            self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), 0)
            events = v.log_events(log)
            self.assertEqual(sum(e[0] == TICK for e in events), 1)
            self.assertEqual(events[0][0], TICK)
            if world != 0x8c:
                self.assertEqual(events[1:], [(MU_WP_MOVE, 0)])
            else:
                self.assertEqual(events[1][0], 0x16caeae if typ == 0x13 else 0x16cacfc)

    def test_log_capacity_preserves_state_and_rng(self):
        def run(capacity, fn):
            log = v.new_log(capacity)
            rng = v.MsvcRand(7)
            obj = C.create_string_buffer(v.OBJ_SIZE)
            struct.pack_into('<ifff', obj, 0x5c, 0, 0, 0, 0)
            fn(obj, v.RAND_FN(lambda ctx: rng()), log)
            self.assertLessEqual(log.count, capacity)
            return obj.raw, rng.seed
        bone = p.BONE(lambda ctx, k, local, out: [out.__setitem__(q, k + q) for q in range(3)] and None)
        cases = []
        for typ in (0xf, 0x10, 0xa5):
            def ok(obj, rnd, log, typ=typ):
                struct.pack_into('<i', obj, 0x5c, typ)
                for _ in range(120):
                    self.lib.mu_old_kethotum_visual(obj, 0, 1, 1234.5, rnd, bone, None, C.byref(log))
            cases.append(ok)
        for typ in (0xa5, 0xb5):
            def bk(obj, rnd, log, typ=typ):
                struct.pack_into('<i', obj, 0x5c, typ)
                model = p.c_model(4, [0.3] * 8, [3] * 8)
                inputs = p.Inputs(0x88, (C.c_float * 3)(0, 0, 0), 0.1, C.pointer(model), rnd, None, 0, 15)
                for _ in range(60):
                    self.lib.mu_burning_kethotum_move(obj, 0, C.byref(inputs), C.byref(log))
                    self.lib.mu_burning_kethotum_visual(obj, 0, 1, rnd, None, C.byref(log))
            cases.append(bk)
        for fn in cases:
            results = [run(capacity, fn) for capacity in (0, 1, 64)]
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-p-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_p.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 10000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(p.MUTANTS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
