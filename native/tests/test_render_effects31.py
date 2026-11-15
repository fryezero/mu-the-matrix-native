"""Existing world and skill consumers: bounded pools, original instructions and real raster."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_particles as pt
import validate_render_effects31 as proof


class Native(unittest.TestCase):
    def test_native_pool_bitmaps_and_raster(self):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/libmunative.a',
                        'build/libmusession_world.a'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            report = pt.Report()
            proof.native_checks(proof.build_host(tmp), proof.bitmap_fixture(tmp), report)
        self.assertTrue(all(f['cases']==f['equal'] for f in report.families.values()),report.families)
        self.assertEqual(report.families['native_particles']['cases'],11)
        self.assertEqual(report.families['native_joints']['cases'],6)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        for directory in ('reconstructed/particles','reconstructed/joints','reconstructed/combat'):
            subprocess.run(['make','-s','-C',str(ROOT/directory)],check=True,capture_output=True)
        result = proof.run(20)
        self.assertTrue(result['all_equal'],result['families'])


if __name__=='__main__':
    unittest.main()
