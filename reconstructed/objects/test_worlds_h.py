"""Worlds 64/82 lifecycle dispatch on synthetic objects; private instruction check."""
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


class WorldsHTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make', '-s', '-C', str(ROOT / 'reconstructed/objects')], check=True)
        cls.lib = v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}').dll

    def create(self, world, typ):
        rec = v.Record()
        rec.type = typ
        rec.position[:] = [100, 200, 300]
        rec.scale = 2
        out = C.create_string_buffer(v.OBJ_SIZE)
        sector = C.c_int32()
        log = v.new_log()
        status = self.lib.mu_obj_create(C.byref(rec), world, out, C.byref(sector), 0, C.byref(log))
        self.assertEqual(status, 0)
        return out

    def test_public_create_dispatch_and_move_dispatch(self):
        duel = self.create(64, 32)
        world82 = self.create(82, 6)
        for obj in (duel, world82):
            self.assertEqual(struct.unpack_from('<f', obj.raw, 0xc0)[0], -300)
        duel = self.create(64, 34)
        fn = v.RAND_FN(lambda ctx: 0)
        speed = v.SPEED_FN(lambda ctx, typ, action: 0)
        for world, obj in [(64, duel), (82, world82)]:
            inputs = v.MoveInputs()
            inputs.world = world
            inputs.scene_state = 6
            inputs.has_model = 1
            inputs.rand_fn = fn
            inputs.speed = speed
            log = v.new_log()
            self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), 0)
            self.assertEqual(struct.unpack_from('<i', obj.raw, 0x68)[0], -2)
            if world == 64:
                lights = [e for e in v.log_events(log) if e[0] == 0x16cacfc]
                self.assertEqual(len(lights), 1)
                self.assertEqual(lights[0][2:4], (v.bits(100), v.bits(200)))

    def test_bounded_logs_keep_rng_and_invalid_scatter_is_safe(self):
        import validate_worlds_h as h
        self.lib = h.bind(v.Library(ROOT / f'reconstructed/objects/libobjects.{v.SUFFIX}')).dll
        fn = self.lib.mu_world82_visual
        for typ in (0, 3, 4, 6, 47, 48):
            outcomes = []
            for capacity in (0, 1, 64):
                obj = self.create(82, typ)
                state = v.MsvcRand(1)
                rnd = v.RAND_FN(lambda ctx: state())
                log = v.new_log(capacity)
                fn(obj, 0, 82, 1, 0, rnd, None, C.byref(log))
                self.assertLessEqual(log.count, capacity)
                outcomes.append((obj.raw, state.seed))
            self.assertEqual(outcomes[0], outcomes[2])
            self.assertEqual(outcomes[1], outcomes[2])
        obj = self.create(82, 48)
        struct.pack_into('<f', obj, 0xa0, 0)
        rnd = v.RAND_FN(lambda ctx: 0)
        log = v.new_log()
        self.assertEqual(fn(obj, 0, 82, 1, 0, rnd, None, C.byref(log)), 1)
        self.assertEqual(log.count, 0)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-h-test-') as directory:
            report = Path(directory) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_h.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 6000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 19)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            subprocess.run([sys.executable, str(ROOT / 'scripts/world_handler_coverage.py')], check=True)
