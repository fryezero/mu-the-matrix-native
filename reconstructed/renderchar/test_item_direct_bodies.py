"""Early-body recipes must preserve entry fields and skip every glow/tail phase."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_renderchar as base
import gen_item_bodies as gen
import validate_item_direct_bodies as direct
import validate_renderchar as v


class ItemDirectBodies(unittest.TestCase):
    def test_early_body_preserves_entry_shade_and_level(self):
        lib = base.lib()
        case = v.classify_case(0x27b8, v.CLASSIFY[0])
        case.update(model_level=37, model_shade=tuple(map(v.f2u, (0.25, 0.5, 0.75))))
        status, expected = v.c_stream(lib, case)
        self.assertEqual(status, 0)
        self.assertEqual(len(expected), 1)
        self.assertEqual(expected[0][3:5], (37, case['model_shade']))
        for level in range(16):
            for record in (None, (0, 0x26, 0), (6, 0x5b, 0)):
                self.assertEqual(v.c_stream(lib, dict(case, item_level=level << 3, option1=1,
                                                     ext=0x33, record=record)), (status, expected))
        for t in gen.DIRECT_TYPES:
            self.assertEqual(lib.mu_rc_item_special(t), 0, hex(t))

    def test_exact_white_selects_the_body_entry(self):
        lib = base.lib()
        for t in gen.DIRECT_WHITE_TYPES:
            case = v.classify_case(t, v.CLASSIFY[0])
            for word, entry in ((0x3f7fffff, 'MESH'), (0x3f800000, 'BODY'), (0x3f800001, 'MESH')):
                status, draws = v.c_stream(lib, dict(case, light=(word,) * 3))
                self.assertEqual(status, 0)
                self.assertEqual(draws[-1][0], entry, (hex(t), hex(word)))

    def test_part_six_is_red_only_on_the_mesh_branch(self):
        lib = base.lib()
        for t in gen.DIRECT_WHITE_TYPES:
            case = v.classify_case(t, v.CLASSIFY[0])
            status, draws = v.c_stream(lib, dict(case, a12=6))
            self.assertEqual(status, 0)
            self.assertEqual(draws[-1][2], tuple(map(v.f2u, (1.0, 0.1, 0.1))))
            status, draws = v.c_stream(lib, dict(case, a12=6, light=(v.f2u(1.0),) * 3))
            self.assertEqual((status, draws[-1][0]), (0, 'BODY'))
            self.assertEqual(draws[-1][2], (v.f2u(1.0),) * 3)

    def test_early_body_writes_back_its_last_model_fields(self):
        case = v.classify_case(0x27b8, v.CLASSIFY[0])
        status, stream, model = direct.c_model(base.lib(), case)
        self.assertEqual(status, 0)
        last = stream[-1]
        self.assertEqual(model, last[2] + (last[3] & 0xffffffff,) + last[4] + (last[5],))
        self.assertNotEqual(model[:3], tuple(case['model_light']))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'direct.json'
            subprocess.run([sys.executable, str(base.ROOT/'scripts/validate_item_direct_bodies.py'),
                            '--mutations', '--output', str(output)], check=True, capture_output=True)
            report = json.loads(output.read_text())
        self.assertEqual(report['families']['bodies']['cases'], 292*len(direct.TYPES))
        self.assertEqual(report['families']['records']['cases'], 512*len(direct.TYPES))
        self.assertEqual(report['families']['lights']['cases'], 144*len(direct.TYPES))
        self.assertEqual(report['families']['frames']['cases'], 64*len(direct.TYPES))
        self.assertEqual(report['families']['parts']['cases'], 288)
        self.assertEqual(report['families']['exits']['cases'], 64*len(direct.TYPES))
        self.assertTrue(all(f['mismatches'] == 0 for f in report['families'].values()))
        self.assertEqual(set(report['mutants']), set(direct.MUTANTS) | {'exit-carry'})
        self.assertTrue(all(report['mutants'].values()))
