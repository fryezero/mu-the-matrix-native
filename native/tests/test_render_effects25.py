"""RENDER-EFFECTS-025: explicit missing-name state and clouds/28."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_render_effects25 as proof
import validate_particles as pt

PRIVATE = os.environ.get('MU_RECOVERY_INTEGRATION') == '1'


class Native(unittest.TestCase):
    def test_scoped_particle_requests_have_consumers(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'reconstructed/particles')],
                       check=True, capture_output=True)
        lib = pt.load_library(ROOT/('reconstructed/particles/libclient_particles.'+pt.SUFFIX))
        census = proof.request_census(lib)
        self.assertEqual(census['programs'], 96)
        self.assertEqual(census['missing_programs'], [])
        self.assertEqual(census['unresolved'], [])
        self.assertTrue(all(p['supported'] for p in census['pairs'].values()), census)

    def test_explicit_pre_bone_record_and_cloud_raster(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/libmunative.a',
                        'build/libmusession_world.a'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            report = pt.Report()
            proof.native_check(proof.build_host(tmp), proof.cloud_fixture(tmp), report)
        self.assertEqual(report.families['native']['cases'], 1)
        self.assertEqual(report.families['native']['first_failures'], [])
        self.assertEqual(report.families['native']['equal'], 1)


@unittest.skipUnless(PRIVATE, 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        for directory in ('native', 'reconstructed/particles', 'reconstructed/renderchar'):
            subprocess.run(['make', '-s', '-C', str(ROOT/directory)], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'report.json'
            subprocess.run([sys.executable, str(ROOT/'scripts/validate_render_effects25.py'), '--cases', '20',
                            '--output', str(path)], check=True, capture_output=True)
            report = json.loads(path.read_text())
        self.assertTrue(report['all_equal'])
        self.assertEqual(report['cases'], 202)


if __name__ == '__main__':
    unittest.main()
