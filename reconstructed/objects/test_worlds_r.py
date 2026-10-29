"""RENDER-WORLDS-R public dispatch, bounded logging and private instruction comparisons."""
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
import validate_worlds_r as r
MU_WR_CREATE, TICK, LIGHT = 0x00e432d9, 0x12b4dd3, 0x16cacfc


class WorldsRTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = r.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll

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

    def test_public_create_defers_scorched_canyon_and_runs_the_others(self):
        out, events = self.create(0x83, 0x6a)
        self.assertEqual(events, [(MU_WR_CREATE, 0)])
        self.assertEqual(out.raw[0x0a], 0)   # the class create has not run yet (it draws from the RNG)
        out, events = self.create(0x84, 0x1e)
        self.assertEqual(events, [])
        self.assertEqual(struct.unpack_from('<f', out.raw, 0xa0)[0], 3.25)
        out, _ = self.create(0x85, 0xa3)
        self.assertEqual(struct.unpack_from('<i', out.raw, 0x68)[0], -2)
        out, _ = self.create(0x86, 0)
        self.assertEqual((out.raw[0x0a], struct.unpack_from('<f', out.raw, 0xc0)[0]), (1, -150.0))

    def test_public_move_ticks_once_then_runs_the_class(self):
        rnd = v.RAND_FN(lambda ctx: 0)
        speed = v.SPEED_FN(lambda ctx, t, a: 0.25)
        for world, typ, light in [(0x83, 0xa0, 3), (0x84, 0, None), (0x85, 6, None), (0x86, 0x3f, 2),
                                  (0x86, 0x48, None)]:
            obj, _ = self.create(world, typ)
            inputs = v.MoveInputs()
            inputs.world, inputs.has_model, inputs.scene_state = world, 1, 6
            inputs.rand_fn, inputs.speed, inputs.time = rnd, speed, 1000
            log = v.new_log()
            self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), 0)
            events = v.log_events(log)
            self.assertEqual(events[0][0], TICK)
            self.assertEqual([e[0] for e in events[1:]], [LIGHT] if light else [])
            if light:
                self.assertEqual(events[1][-1], light)

    def test_log_capacity_preserves_state_and_rng(self):
        def run(capacity, fn):
            log = v.new_log(capacity)
            rng = v.MsvcRand(7)
            obj = C.create_string_buffer(v.OBJ_SIZE)
            struct.pack_into('<ifff', obj, 0x5c, 0, 0, 0, 0)
            fn(obj, v.RAND_FN(lambda ctx: rng()), log)
            self.assertLessEqual(log.count, capacity)
            return obj.raw, rng.seed
        bone = r.BONE(lambda ctx, k, local, out: [out.__setitem__(q, k + q) for q in range(3)] and None)
        cases = []
        for typ in (0x1e, 0x38, 0x3b, 0x3c, 0x41, 0x46, 0x49):
            def ga(obj, rnd, log, typ=typ):
                struct.pack_into('<i', obj, 0x5c, typ)
                for k in range(120):
                    self.lib.mu_gray_aida_move(obj, 0, 0x86, rnd, None, C.byref(log))
                    self.lib.mu_gray_aida_visual(obj, 0, 1, float(k * 7), rnd, bone, None, C.byref(log))
            cases.append(ga)
        for typ in (0, 4, 0xa):
            def rs(obj, rnd, log, typ=typ):
                struct.pack_into('<i', obj, 0x5c, typ)
                for _ in range(30):
                    self.lib.mu_red_smoke_icarus_visual(obj, 0, 1, bone, None, C.byref(log))
            cases.append(rs)
        for fn in cases:
            results = [run(capacity, fn) for capacity in (0, 1, 64)]
            self.assertEqual(results[0], results[1])
            self.assertEqual(results[0], results[2])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-r-test-') as td:
            report = Path(td) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_r.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(f['cases'] for f in result['families'].values()), 12000)
            self.assertTrue(all(f['cases'] == f['equal'] and f['stopped'] == 0 for f in result['families'].values()))
            self.assertEqual(len(result['mutants']), len(r.MUTANTS))
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))


if __name__ == '__main__':
    unittest.main()
