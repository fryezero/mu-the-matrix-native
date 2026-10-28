"""Part 8 membership, capacity, lighting and original-instruction evidence."""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_renderchar as base
import validate_item_next as next_items

class ItemNext(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lib=base.lib()
        cls.v=next_items.v
    item=base.RenderCharLibrary.item
    draws=base.RenderCharLibrary.draws

    def test_rank5_and_next_bodies_keep_domain_bounds(self):
        for t in (*next_items.gen.NEXT_TYPES,*next_items.pose.TYPES):
            self.assertEqual(self.draws(self.item(type=t))[0],0,hex(t))
            self.assertEqual(self.draws(self.item(type=t,a10=0))[0],2,hex(t))
            self.assertEqual(self.draws(self.item(type=t,a11=0))[0],2,hex(t))
            self.assertEqual(self.draws(self.item(type=t,select=1))[0],2,hex(t))
        self.assertEqual(len(self.draws(self.item(type=0x1c24))[1]),2)
        self.assertEqual(len(self.draws(self.item(type=0x1c26))[1]),4)

    def test_next_links_bounds(self):
        c=next_items.clusters
        for t,n in ((0x10f0,8),(0x16f5,2)):
            for capacity in (0,1,n):
                out,count=(c.Effect*10)(),C.c_int32()
                out[capacity].particle=999
                calls=[]
                @c.RANDOM
                def rand(_):calls.append(7);return 7
                status=self.lib.mu_rc_link_effects_time(t,C.c_float(500),rand,None,out,capacity,C.byref(count))
                self.assertEqual((status,count.value,len(calls)),(0 if capacity==n else 3,n,1))
                self.assertEqual(out[capacity].particle,999)
                self.assertEqual(self.lib.mu_rc_link_supported(t),1)

    @unittest.skipUnless(os.environ.get('MU_RECOVERY_INTEGRATION')=='1','original captures are opt-in')
    def test_private_original_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'next.json'
            subprocess.run([sys.executable,str(base.ROOT/'scripts/validate_item_next.py'),'--mutations','--output',str(output)],check=True,capture_output=True)
            report=json.loads(output.read_text())
            self.assertEqual(report['families']['bodies']['cases'],2336)
            self.assertEqual(report['families']['rank5']['cases'],11096)
            self.assertEqual(report['families']['rank5_records']['cases'],760)
            self.assertEqual(report['families']['links']['cases'],800)
            self.assertTrue(all(f['mismatches']==0 for f in report['families'].values()))
            self.assertEqual(len(report['mutants']),9)
            self.assertTrue(all(report['mutants'].values()))
