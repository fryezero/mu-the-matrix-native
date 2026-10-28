"""Worlds 62/63 lifecycle dispatch on synthetic objects; private instruction check."""
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


class WorldsGTests(unittest.TestCase):
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
        santa = self.create(62, 0xc)
        self.assertEqual(struct.unpack_from('<f', santa.raw, 0xc0)[0], -300)
        vulcanus = self.create(63, 0x46)
        self.assertEqual(vulcanus.raw[0xa], 1)
        vulcanus = self.create(63, 6)
        self.assertEqual(struct.unpack_from('<f', vulcanus.raw, 0xc0)[0], -300)
        santa = self.create(62, 0x10)
        fn = v.RAND_FN(lambda ctx: 0)
        speed = v.SPEED_FN(lambda ctx, typ, action: 0)
        for world, obj in [(62, santa), (63, vulcanus)]:
            inputs = v.MoveInputs()
            inputs.world = world
            inputs.scene_state = 6
            inputs.has_model = 1
            inputs.rand_fn = fn
            inputs.speed = speed
            log = v.new_log()
            self.assertEqual(self.lib.mu_obj_move(obj, 0, C.byref(inputs), C.byref(log)), 0)
        self.assertEqual(santa.raw[0xbc:0xc0], struct.pack('<f', 0.06))
        self.assertEqual(struct.unpack_from('<i', vulcanus.raw, 0x68)[0], -2)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'private instruction captures required')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory(prefix='worlds-g-test-') as directory:
            report = Path(directory) / 'report.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts/validate_worlds_g.py'), '--cases', '1000',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            result = json.loads(report.read_text())
            self.assertEqual(sum(r['cases'] for r in result['families'].values()), 6000)
            self.assertTrue(all(r['cases'] == r['equal'] and r['stopped'] == 0 for r in result['families'].values()))
            self.assertEqual(len(result['mutants']), 13)
            self.assertTrue(all(m['detected'] > 0 and m['stopped'] == 0 for m in result['mutants']))
            subprocess.run([sys.executable, str(ROOT / 'scripts/world_handler_coverage.py')], check=True)
