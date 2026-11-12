"""EFFECTS-026: later item particle consumers and explicit census domain."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import validate_render_effects26 as proof
import validate_particles as pt


class Native(unittest.TestCase):
    def test_five_consumers_and_full_inventory(self):
        subprocess.run(['make','-s','-C',str(ROOT/'reconstructed/particles')],check=True,capture_output=True)
        lib=pt.load_library(ROOT/('reconstructed/particles/libclient_particles.'+pt.SUFFIX))
        census=proof.request_census(lib)
        self.assertEqual(census['programs'],110)
        self.assertEqual(census['particle_pairs'],37)
        self.assertEqual(census['missing_programs'],[])
        self.assertEqual(census['unresolved'],[])
        self.assertTrue(all(p['supported'] for p in census['pairs'].values()),census)
        self.assertEqual(lib.mu_pt_kind_supported(0xdead,0),0)

    def test_real_native_pool_owner_and_raster(self):
        subprocess.run(['make','-s','-C',str(ROOT/'native'),'build/libmunative.a',
                        'build/libmusession_world.a'],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            r=pt.Report();proof.native_check(proof.build_host(tmp),proof.bitmap_fixture(tmp),r)
        self.assertEqual(r.families['native']['cases'],5)
        self.assertEqual(r.families['native']['equal'],5,r.families)


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        for directory in ('reconstructed/particles','reconstructed/renderchar','native'):
            subprocess.run(['make','-s','-C',str(ROOT/directory)],check=True,capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'report.json'
            subprocess.run([sys.executable,str(ROOT/'scripts/validate_render_effects26.py'),'--cases','20',
                            '--output',str(out)],check=True,capture_output=True)
            result=json.loads(out.read_text())
        self.assertTrue(result['all_equal'])
        self.assertEqual(result['cases'],348)


if __name__=='__main__':unittest.main()
