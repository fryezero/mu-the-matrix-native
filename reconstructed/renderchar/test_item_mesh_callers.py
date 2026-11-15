"""Low-level callers that draw two meshes themselves below glow level three."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import item_mesh_callers as callers
import validate_item_mesh_callers as check
import validate_renderchar as v


class ItemMeshCallers(unittest.TestCase):
    def test_two_meshes_below_glow_level_three(self):
        lib = base.lib()
        self.assertEqual(callers.TYPES, (0x27ef, 0x27f0, 0x27f1, 0x27f2, 0x286e, 0x286f, 0x2874))
        for t, texture in ((0x27ef, 0x81d4), (0x2874, 0x81d5), (0x27f1, 0x81d6), (0x286f, 0x81d7)):
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
            case = v.classify_case(t, v.CLASSIFY[0])
            case.update(u=v.f2u(0.25), v=v.f2u(-0.5), blend_mesh=3, object_alpha=v.f2u(0.75))
            status, stream = v.c_stream(lib, dict(case, item_level=16))
            self.assertEqual(status, 0)
            self.assertEqual([draw[0] for draw in stream], ['MESH', 'MESH'])
            first, second = stream[0][1], stream[1][1]
            self.assertEqual(first, [0, 2, v.f2u(0.75), 3, case['blend_light'], 0, 0, 0xffffffff])
            self.assertEqual(second, [0, 2, v.f2u(0.75), 0xfffffffe, case['blend_light'], v.f2u(0.25),
                                      v.f2u(-0.5), texture])
            # From glow level three the ordinary helper chain draws the body.
            status, stream = v.c_stream(lib, dict(case, item_level=24))
            self.assertEqual((status, stream[0][0]), (0, 'BODY'))
        for t in (0x130b, 0x2875):
            self.assertEqual(lib.mu_rc_item_special(t), 1, hex(t))

    def test_light_helper_and_two_meshes(self):
        lib = base.lib()
        self.assertEqual(callers.HELPER_TYPES, (0x2406, 0x2477))
        for t, swap in ((0x2406, False), (0x2477, True)):
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))
            case = v.classify_case(t, v.CLASSIFY[0])
            case.update(u=v.f2u(0.25), v=v.f2u(-0.5), blend_mesh=3, object_alpha=v.f2u(0.75), object_hidden=-1)
            status, stream = v.c_stream(lib, dict(case, item_level=16))
            self.assertEqual((status, [draw[0] for draw in stream]), (0, ['BODY', 'MESH', 'MESH']))
            # The helper and both meshes carry the light argument as the model light.
            self.assertTrue(all(tuple(draw[2]) == tuple(case['light']) for draw in stream))
            self.assertEqual(stream[1][1], [0, 2, v.f2u(0.75), 3, case['blend_light'], v.f2u(0.25), v.f2u(-0.5), 0xffffffff])
            u, w = (v.f2u(-0.5), v.f2u(0.25)) if swap else (v.f2u(0.25), v.f2u(-0.5))
            self.assertEqual(stream[2][1], [1, 0x46, v.f2u(base.f32(0.7)), 3, case["blend_light"], u, w, 0xffffffff])

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'mesh-callers.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_mesh_callers.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        n = len(check.TYPES)
        for name, per_type in (('bodies', 292), ('records', 512), ('levels', 1644), ('exits', 64),
                               ('original_sites', 9)):
            self.assertEqual(report['families'][name]['cases'], per_type * n, name)
        self.assertEqual(report['families']['reader_refusals']['cases'], 9)
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(check.MUTANTS))
        self.assertTrue(all(report['mutants'].values()))
