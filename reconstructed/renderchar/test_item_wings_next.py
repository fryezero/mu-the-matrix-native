"""Part 10 visible item recipes and bounded shield output."""
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


class ItemWingsNext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib = base.lib()
        cls.v = clusters.v
    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_admissions_and_existing_domain(self):
        for t in gen.WING_TYPES + gen.VISIBLE_TYPES:
            self.assertEqual(self.draws(self.item(type=t))[0],0,hex(t))
            for args in ({'a10':0},{'a11':0},{'select':1},{'object_shadow':1}):
                self.assertEqual(self.draws(self.item(type=t,**args))[0],2,(hex(t),args))

    def test_wings_suppress_glow_and_keep_two_colours(self):
        colours = ((0.9,0.1,0.2),(0.4,0.5,1),(1,1,1),(0.4,1,0.6),(1,0.8,0.4),(1,0.4,1))
        for t,rgb in zip(gen.WING_TYPES,colours):
            for level in (0,7,13,15):
                status,draws = self.draws(self.item(type=t,item_level=level<<3))
                self.assertEqual((status,len(draws)),(0,2))
                self.assertEqual([d.flags for d in draws],[2,0x44])
                self.assertEqual(tuple(draws[0].body_light),tuple(C.c_float(x).value for x in rgb))

    def test_atlas_signed_frames_and_pulse_capacity(self):
        for t in (0x2002,0x2004,0x1f9f,0x1d7c):
            it = self.item(type=t,time=-599,item_level=13<<3,option1=1)
            expected = self.draws(it)[1]
            model = self.v.CModel()
            out,count = (self.v.CDraw*33)(),C.c_int32()
            for capacity in (0,1,len(expected)):
                out[capacity].mesh = 123456
                status = self.lib.mu_rc_item_draws(C.byref(it),C.byref(model),out,capacity,C.byref(count))
                self.assertEqual((status,count.value),(0 if capacity==len(expected) else 3,len(expected)))
                self.assertEqual(out[capacity].mesh,123456)
        _,draws = self.draws(self.item(type=0x2002,time=-599))
        self.assertEqual([draws[2].u,draws[2].v],[C.c_float(-5*C.c_float(0.167).value).value,C.c_float(-4*C.c_float(0.2).value).value])

    def test_shield_count_capacity_and_random_order(self):
        for t in (0x16f7,0x16fb):
            for capacity in (0,1,10):
                out,count = (clusters.Effect*11)(),C.c_int32()
                out[capacity].particle = 123456
                calls = []
                @clusters.RANDOM
                def rand(_):
                    calls.append(7)
                    return 7
                status = self.lib.mu_rc_link_effects_time(t,C.c_float(-500),rand,None,out,capacity,C.byref(count))
                self.assertEqual((status,count.value,len(calls)),(0 if capacity==10 else 3,10,1))
                self.assertEqual(out[capacity].particle,123456)
            bones = list(range(4,11))+[1,2,3] if t==0x16f7 else list(range(4,14))
            self.assertEqual([e.sprite.bone for e in out[:10]],bones)
            self.assertEqual(self.lib.mu_rc_link_supported(t),1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','original captures are opt-in')
    def test_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'wings.json'
            subprocess.run([sys.executable,str(base.ROOT/'scripts/validate_item_wings_next.py'),
                            '--mutations','--output',str(path)],check=True,capture_output=True)
            report = json.loads(path.read_text())
            self.assertEqual(report['families']['bodies']['cases'],292*(len(gen.WING_TYPES)+len(gen.VISIBLE_TYPES)))
            self.assertEqual(report['families']['links']['cases'],800)
            self.assertEqual(report['families']['clocks']['cases'],210)
            self.assertEqual(report['families']['position']['cases'],200)
            self.assertTrue(all(f['mismatches']==0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']),12)
            self.assertTrue(all(report['mutants'].values()))
