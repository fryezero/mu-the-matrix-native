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
        self.assertEqual(report.families['native_effects']['cases'],5)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/libmunative.a',
                        'build/libmusession_world.a'],check=True,capture_output=True)

    def test_original_instructions(self):
        for directory in ('reconstructed/particles','reconstructed/joints','reconstructed/combat'):
            subprocess.run(['make','-s','-C',str(ROOT/directory)],check=True,capture_output=True)
        result = proof.run(20)
        self.assertTrue(result['all_equal'],result['families'])
        self.assertEqual(result['census']['frozen_items'],dict(programs=110,particle_pairs=37))
        self.assertEqual(result['census']['world_skill']['supported'],22)

    @unittest.skipUnless(os.environ.get('MU_NATIVE_DATA_DIR'),'requires installed read-only native data')
    def test_installed_transition_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            images=Path(tmp)/'images'; images.mkdir()
            host=proof.build_host(tmp); root=proof.bitmap_fixture(tmp)
            result=subprocess.run([str(host),str(root),str(images),os.environ['MU_NATIVE_DATA_DIR']],
                                  capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr[-2000:])
            rows=[json.loads(s) for s in result.stdout.splitlines()]
            self.assertEqual(sum(bool(r.get('installed')) for r in rows),2)



if __name__=='__main__':
    unittest.main()
