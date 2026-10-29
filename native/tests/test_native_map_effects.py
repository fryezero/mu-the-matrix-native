"""RENDER-EFFECTS-008: the map-object effect table in the production host (loader, attach 0x0183067e, update)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_native_effect import billboard, particle_system  # noqa: E402
from test_native_render_effects6 import bmd  # noqa: E402

# Synthetic table rows (world, type, index, path, x, y, z, rx, ry, rz, scale, bone, follow, tint, start, actions):
# type 67's second path ends in a space (Win32 drops it), type 70's file is absent.
TABLE = '''# synthetic
#world\ttype\tindex\tpath\tx\ty\tz\trx\try\trz\tscale\tbone\tfollow\ttint\tstart\tactions
118\t62\t0\tData\\\\Effect\\\\fxa.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t50.0\t0\t1\t0\t00220000\t-
118\t67\t0\tData\\\\Effect\\\\fxb.ein\t0.0\t0.0\t10.0\t1.25\t0.0\t0.0\t60.0\t0\t1\t0\t00000000\t-
118\t67\t1\tData\\\\Effect\\\\fxa.ein \t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t40.0\t3\t0\t1\t00000000\t0,2
118\t70\t0\tData\\\\Effect\\\\missing.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t50.0\t0\t1\t0\t00000000\t-
131\t62\t0\tData\\\\Effect\\\\fxb.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t30.0\t0\t1\t0\t00000000\t-
200\t5\t0\tData\\\\Effect\\\\fxa.ein\t0.0\t0.0\t0.0\t0.0\t0.0\t0.0\t1.0\t0\t1\t0\t00000000\t-
'''


class MapEffectsHost(unittest.TestCase):
    def test_table_attach_and_update(self):
        subprocess.run(['make', '-s', '-C', str(NATIVE), 'build/map-effects-host'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / 'model.bmd'
            model.write_bytes(bmd())
            root, lang = Path(td) / 'root', Path(td) / 'lang'
            (root / 'Data/Effect').mkdir(parents=True)
            lang.mkdir()
            (root / 'Data/Effect/fxa.ein').write_text(json.dumps(particle_system(Scale=2.0)))
            (root / 'Data/Effect/fxb.ein').write_text(json.dumps(billboard()))
            (lang / 'mapeffects.tsv').write_text(TABLE)
            out = subprocess.run([str(NATIVE / 'build/map-effects-host'), str(model), str(root), str(lang)],
                                 check=True, capture_output=True, text=True).stdout
        rows = [json.loads(line) for line in out.splitlines()]
        self.assertEqual(rows[0], {'table': True, 'worlds': 3, 'types': 5, 'entries': 6})
        deep, canyon, absent = rows[1:]
        # every object of the world is cleared; found types (62, 67, 70) are primed after their vector
        self.assertEqual((deep['cleared'], deep['requested'], deep['invalid'], deep['attached'], deep['primed']),
                         (5, 5, 1, 4, 4))
        # sector order (object 0 is in sector 48), vector order, bone/follow from the table, never timed;
        # template scale = the requested scale
        self.assertEqual(deep['links'], [[1, 0, 1, 0, 50.0], [2, 0, 1, 0, 60.0], [2, 3, 0, 0, 40.0],
                                         [0, 0, 1, 0, 50.0]])
        # hidden markers (+0x68 = -2) are posed by RenderObject's animation: every effect follows its bone
        self.assertEqual(deep['unposed'], 0)
        self.assertEqual(deep['updates'], 4 * 30)
        self.assertEqual((deep['external'], deep['owner_visible'], deep['instances']), (4, 4, 4))
        self.assertEqual((canyon['attached'], canyon['updates'], canyon['unposed'], canyon['external']),
                         (1, 30, 0, 1))
        self.assertEqual((absent['cleared'], absent['requested'], absent['attached'], absent['instances']),
                         (0, 0, 0, 0))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
    def test_original_instructions_and_compiled_mutants(self):
        root = NATIVE.parent
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / 'report.json'
            subprocess.run([sys.executable, str(root / 'scripts/validate_map_effects.py'), '--cases', '300',
                            '--mutations', '--output', str(report)], check=True, capture_output=True)
            r = json.loads(report.read_text())
        self.assertTrue(r['all_equal'])
        self.assertTrue(r['all_mutants_caught'])
        self.assertEqual(r['instruction_cases'], 300)
        self.assertEqual(len(r['mutants']), 14)


if __name__ == '__main__':
    unittest.main()
