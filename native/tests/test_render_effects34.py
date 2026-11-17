"""Consumer pairs already requested by world, item and Muun producers: native pools, bitmaps, raster and the
original instructions (RENDER-EFFECTS-034)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
import validate_particles as pt
import validate_render_effects34 as proof


class Native(unittest.TestCase):
    def test_native_pools_bitmaps_follow_point_and_raster(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/libmunative.a',
                        'build/libmusession_world.a'], check=True, capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            report = pt.Report()
            proof.native_checks(proof.build_host(tmp), proof.bitmap_fixture(tmp), report)
        self.assertTrue(all(f['cases'] == f['equal'] for f in report.families.values()), report.families)
        self.assertEqual(report.families['native_particles']['cases'], len(proof.KINDS))
        self.assertEqual(report.families['native_joints']['cases'], len(proof.JOINTS))
        self.assertEqual(report.families['native_sprites']['cases'], 4)
        self.assertEqual(report.families['native_ledger']['cases'], 1)

    def test_group_table_names_each_pair_once(self):
        pairs = proof.KINDS + proof.JOINTS
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertEqual((len(proof.KINDS), len(proof.JOINTS)), (23, 4))
        self.assertEqual(sorted(sum(proof.GROUPS.values(), [])), sorted(proof.KINDS))


@unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION') == '1', 'requires pinned private instructions')
class ClientComparison(unittest.TestCase):
    def test_original_instructions(self):
        subprocess.run(['make', '-s', '-C', str(ROOT/'native'), 'build/libmunative.a',
                        'build/libmusession_world.a'], check=True, capture_output=True)
        for directory in ('reconstructed/particles', 'reconstructed/joints'):
            subprocess.run(['make', '-s', '-C', str(ROOT/directory)], check=True, capture_output=True)
        result = proof.run(20)
        self.assertTrue(result['all_equal'], result['families'])
        self.assertEqual(len(result['census']), 27)
        self.assertTrue(all(row['supported'] for row in result['census']))


if __name__ == '__main__':
    unittest.main()
