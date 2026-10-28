"""Worked examples and opt-in full instruction comparison for part 3."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base


class ItemClusters(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_renderchar as v
        cls.v, cls.lib = v, base.lib()

    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_armour_flag_branch_and_high_passes(self):
        # Helm/armour/pants set 40 share the object-alpha, hidden-mesh base rule.
        for t in (0x190d,0x1b0d,0x1d0d):
            s,d = self.draws(self.item(type=t,alpha=0.25,object_alpha=0.75,item_level=13<<3))
            self.assertEqual(s,0)
            self.assertEqual((d[0].flags,d[0].alpha,d[0].hidden),(2,0.75,0))
            self.assertEqual([x.flags for x in d],[2,0x240,0x1040,0x48,0x44])
            s,d = self.draws(self.item(type=t,alpha=0.25,object_alpha=0.75,render_type=0x40042))
            self.assertEqual((s,d[0].flags,d[0].alpha,d[0].hidden),(0,0x40042,0.25,-1))

    def test_wing_levels_and_constant_mesh_colours(self):
        for t,n in ((0x234a,3),(0x241d,4)):
            s,d = self.draws(self.item(type=t,item_level=15<<3))
            self.assertEqual((s,len(d)),(0,n))
            self.assertEqual([x.entry for x in d],[1,1]+[2]*(n-2))
            self.assertEqual([x.hidden for x in d[:2]],[0,1])
            self.assertEqual(self.draws(self.item(type=t,option1=1))[1][-1].flags,0x42)
        self.assertEqual(self.draws(self.item(type=0x2368))[0],1)

    def test_recipe_bounds_and_explicit_overrides(self):
        import validate_renderchar as v
        it=self.item(type=0x241d)
        model=v.CModel()
        out=(v.CDraw*2)()
        out[1].mesh=999
        n=C.c_int32()
        self.assertEqual(self.lib.mu_rc_item_draws(C.byref(it),C.byref(model),out,1,C.byref(n)),3)
        self.assertEqual((n.value,out[1].mesh),(4,999))
        self.assertEqual(self.draws(self.item(type=0x241d,a10=0,a11=99))[0],2)

    def test_offset_effects_random_order_and_bounds(self):
        import validate_item_clusters as v
        status,calls,n=v.c_effects(self.lib,0x14f0,[0]*32)
        self.assertEqual((status,len(calls),n),(0,20,21))
        self.assertEqual(calls[0][2],(v.v.f2u(-180),v.v.f2u(-40),0))
        self.assertEqual(v.c_effects(self.lib,0x14f0,[1]*32)[2],11)
        self.assertEqual(len(v.c_effects(self.lib,0x12fb,[1]*32)[1]),7)
        self.assertEqual(len(v.c_effects(self.lib,0x12fb,[2]*32)[1]),5)
        self.assertEqual(v.c_effects(self.lib,0xae6,[]),(1,[],0))
        out=(v.Effect*2)()
        out[1].particle=999
        count=C.c_int32()
        @v.RANDOM
        def random(_):return 0
        self.assertEqual(self.lib.mu_rc_link_effects(0x14f0,random,None,out,1,C.byref(count)),3)
        self.assertEqual((count.value,out[1].particle),(20,999))

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','original captures are opt-in')
    def test_private_original_instructions(self):
        import gen_item_bodies as gen
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'clusters.json'
            subprocess.run([sys.executable,str(base.ROOT/'scripts/validate_item_clusters.py'),
                            '--mutations','--output',str(output)],check=True,capture_output=True)
            r=json.loads(output.read_text())
            self.assertFalse(r['screen_failures'])
            self.assertEqual(r['families']['bodies']['cases'],len(gen.REVIEWED_TYPES)*292)
            self.assertEqual(r['families']['links']['cases'],800)
            self.assertEqual(r['families']['transforms']['cases'],200)
            self.assertEqual(len(r['mutants']),8)
            self.assertTrue(all(r['mutants'].values()))
