"""Ranked armour omissions, sprite-chain ordering and independent instruction checks."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base


class ItemRanked(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import validate_item_ranked as ranked
        cls.ranked, cls.v, cls.lib = ranked, ranked.v, base.lib()

    item = base.RenderCharLibrary.item
    draws = base.RenderCharLibrary.draws

    def test_rank9_omits_ancient_but_keeps_glow(self):
        for t in (0x199f, *range(0x19a3, 0x19ae)):
            status, plain = self.draws(self.item(type=t, item_level=13<<3))
            status2, ancient = self.draws(self.item(type=t, item_level=13<<3, ext_option=1))
            self.assertEqual((status,status2,len(ancient)),(0,0,len(plain)))
            self.assertGreater(len(plain),1)
            self.assertEqual([d.flags for d in ancient], [d.flags for d in plain])
            self.assertNotIn(0x840, [d.flags for d in ancient])

    def test_ranked_types_keep_override_and_pose_refusals(self):
        import gen_item_bodies as gen
        for t in gen.RANKED_TYPES:
            self.assertEqual(self.draws(self.item(type=t, a10=0))[0], 2)
        for t in (*range(0x1c24,0x1c35),0x1c44,0x1c7a):
            self.assertEqual(self.draws(self.item(type=t)), (1,[]))

    def test_chain_random_order_and_final_white(self):
        c = self.ranked.clusters
        for value, count, random_calls in ((0,14,15),(1,7,8)):
            status, effects, consumed = c.c_effects(self.lib,0xaf9,[value]*32,0)
            self.assertEqual((status,len(effects),consumed),(0,count,random_calls))
            self.assertEqual(effects[-1][1],8)
        status, effects, consumed = c.c_effects(self.lib,0x12f9,[0]*32,0)
        self.assertEqual((status,len(effects),consumed),(0,10,1))
        self.assertEqual([e[1] for e in effects],[1,1,2,2,3,3,4,4,5,5])
        self.assertEqual(effects[-1][4],(self.ranked.v.f2u(1),)*3)
        self.assertNotEqual(effects[-2][4],effects[-1][4])

    def test_chain_capacity_preserves_sentinel_and_random_order(self):
        c = self.ranked.clusters
        for capacity in (0,1,9,10):
            out, count = (c.Effect*11)(), C.c_int32()
            out[capacity].particle = 999
            consumed = []
            @c.RANDOM
            def rand(_): consumed.append(0); return 0
            status = self.lib.mu_rc_link_effects_time(0x12f9,C.c_float(0),rand,None,out,capacity,C.byref(count))
            self.assertEqual((status,count.value,len(consumed)),(3 if capacity<10 else 0,10,1))
            self.assertEqual(out[capacity].particle,999)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','original captures are opt-in')
    def test_private_original_instructions(self):
        import gen_item_bodies as gen
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'ranked.json'
            subprocess.run([sys.executable,str(base.ROOT/'scripts/validate_item_ranked.py'),
                            '--mutations','--output',str(output)],check=True,capture_output=True)
            report = json.loads(output.read_text())
            self.assertEqual(report['families']['bodies']['cases'],len(gen.RANKED_TYPES)*292)
            self.assertEqual(report['families']['links']['cases'],800)
            self.assertTrue(all(f['mismatches']==0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']),6)
            self.assertTrue(all(report['mutants'].values()))
