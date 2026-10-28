"""Part 7 gear membership, scalar rules, bounds and independent instruction evidence."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base

class ItemGear(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_item_gear as gear
        cls.gear,cls.v,cls.lib=gear,gear.v,base.lib()
    item=base.RenderCharLibrary.item
    draws=base.RenderCharLibrary.draws

    def test_all_readme_stress_loadout_bodies_are_admitted(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('capture',base.ROOT/'native/tools/capture_readme_stress.py')
        capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
        for _,armour,weapon,wing,_,level in capture.KITS:
            group,index=map(int,weapon.split(':'))
            types=[0xae6+g*512+armour for g in range(7,12)]+[0xae6+group*512+index,0x22e6+wing]
            for t in types:
                self.assertEqual(self.draws(self.item(type=t,item_level=level<<3))[0],0,hex(t))

    def test_expanded_membership_and_mesh_override_refusals(self):
        for t in self.gear.gen.EXPANDED_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0],0,hex(t))
            self.assertEqual(self.draws(self.item(type=t,a11=0))[0],2,hex(t))
        for t in (0x230f,0x248e,0x2490,0x2504,0x270f,*self.gear.pose.TYPES):
            self.assertEqual(self.draws(self.item(type=t)),(1,[]))

    def test_flag_branch_clock_crosses_armour_clamp(self):
        # Independent original-stream control that rejected the saturated probe fit.
        status,draws=self.draws(self.item(type=0x218a,render_type=0x40042,time=791240.0))
        self.assertEqual(status,0)
        self.assertEqual(self.v.f2u(draws[5].blend_light),1045510311)
        self.assertEqual(self.v.f2u(draws[3].v),self.v.f2u(0.62))
        self.assertEqual(self.v.f2u(draws[4].u),self.v.f2u(0.62))

    def test_pulse_link_capacity_and_admission(self):
        c=self.gear.clusters
        for t,n in ((0xafa,4),(0xeed,2),(0xeee,4)):
            for capacity in (0,1,n):
                out,count=(c.Effect*5)(),C.c_int32()
                out[capacity].particle=999
                calls=[]
                @c.RANDOM
                def rand(_):calls.append(7);return 7
                status=self.lib.mu_rc_link_effects_time(t,C.c_float(500),rand,None,out,capacity,C.byref(count))
                self.assertEqual((status,count.value,len(calls)),(0 if capacity==n else 3,n,1))
                self.assertEqual(out[capacity].particle,999)
                self.assertEqual(self.lib.mu_rc_link_supported(t),1)
        calls=[]
        @c.RANDOM
        def rand(_):calls.append(0);return 0
        n=C.c_int32()
        self.assertEqual(self.lib.mu_rc_link_effects_time(0xb03,C.c_float(0),rand,None,None,0,C.byref(n)),1)
        self.assertFalse(calls)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','original captures are opt-in')
    def test_private_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'gear.json'
            subprocess.run([sys.executable,str(base.ROOT/'scripts/validate_item_gear.py'),'--mutations','--output',str(output)],check=True,capture_output=True)
            report=json.loads(output.read_text())
            self.assertEqual(report['families']['bodies']['cases'],len(self.gear.gen.EXPANDED_TYPES)*292)
            self.assertEqual(report['families']['links']['cases'],1200)
            self.assertEqual(report['families']['rank5_pose']['cases'],608)
            self.assertEqual(report['families']['rank5_points']['cases'],1216)
            self.assertEqual(report['families']['clocks']['cases'],40)
            self.assertTrue(all(f['mismatches']==0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']),10)
            self.assertTrue(all(report['mutants'].values()))
