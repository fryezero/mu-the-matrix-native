"""Part 9 coverage, bounded command output and pinned instruction comparisons."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base
import gen_item_bodies as gen
import validate_item_clusters as clusters

class ItemCoverage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.v = clusters.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_new_bodies_keep_the_supported_domain(self):
        for t in gen.CLOCK_TYPES + gen.CLUSTER_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0], 0, hex(t))
            for args in ({'a10':0}, {'a11':0}, {'select':1}, {'object_shadow':1}):
                self.assertEqual(self.draws(self.item(type=t,**args))[0], 2, (hex(t),args))

    def test_mesh_pulse_and_capacity(self):
        self.assertEqual(len(self.draws(self.item(type=0x2024))[1]), 2)
        self.assertEqual(len(self.draws(self.item(type=0x1e24))[1]), 3)
        it = self.item(type=0x2024, time=500, item_level=13<<3, option1=1)
        expected = self.draws(it)[1]
        model = self.v.CModel()
        out, count = (self.v.CDraw*33)(), C.c_int32()
        for capacity in (0,1,len(expected)):
            out[capacity].mesh = 123456
            status = self.lib.mu_rc_item_draws(C.byref(it),C.byref(model),out,capacity,C.byref(count))
            self.assertEqual((status,count.value),(0 if capacity==len(expected) else 3,len(expected)))
            self.assertEqual(out[capacity].mesh,123456)

    def test_shield_link_bones_and_capacity(self):
        for capacity in (0,1,9):
            out,count = (clusters.Effect*10)(),C.c_int32()
            out[capacity].particle = 123456
            calls=[]
            @clusters.RANDOM
            def rand(_): calls.append(7); return 7
            status=self.lib.mu_rc_link_effects_time(0x16fa,C.c_float(-500),rand,None,out,capacity,C.byref(count))
            self.assertEqual((status,count.value,len(calls)),(0 if capacity==9 else 3,9,1))
            self.assertEqual(out[capacity].particle,123456)
        self.assertEqual([e.sprite.bone for e in out[:9]],list(range(1,10)))
        self.assertEqual(self.lib.mu_rc_link_supported(0x16fa),1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'coverage.json'
            subprocess.run([sys.executable,str(base.ROOT/'scripts/validate_item_coverage.py'),
                            '--mutations','--output',str(path)],check=True,capture_output=True)
            report=json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'],292*(len(gen.CLOCK_TYPES)+len(gen.CLUSTER_TYPES)))
            self.assertEqual(report['families']['links']['cases'],400)
            self.assertTrue(all(f['mismatches']==0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']),9)
            self.assertTrue(all(report['mutants'].values()))
